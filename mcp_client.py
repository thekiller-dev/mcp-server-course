"""
Client MCP complet (le "chat app" des dernières leçons du cours).

Ce qu'il montre :
  - se connecter à un serveur MCP en stdio
  - lister / appeler des TOOLS depuis une boucle agentique avec Claude
  - lire des RESOURCES pour l'autocomplete et l'injection de contexte (@fichier)
  - récupérer un PROMPT et l'envoyer comme message utilisateur (/format)

Prérequis :
    pip install "mcp[cli]" anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Usage :
    python mcp_client.py                 # mode chat interactif
    python mcp_client.py --demo          # une seule question, sans saisie
"""

import asyncio
import os
import sys
from pathlib import Path

from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("mcp_server.py")
MODEL = "claude-sonnet-4-5"


def mcp_tools_to_anthropic(tools) -> list[dict]:
    """Le JSON Schema produit par le SDK MCP est déjà au bon format :
    on le réutilise tel quel comme input_schema pour l'API Anthropic."""
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        for t in tools
    ]


async def handle_tool_calls(session, response, messages):
    """Exécute les tool_use demandés par Claude et renvoie les tool_result."""
    tool_results = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        print(f"   🔧 {block.name}({block.input})")
        try:
            result = await session.call_tool(block.name, block.input)
            text = "\n".join(
                c.text for c in result.content if getattr(c, "type", "") == "text"
            )
            is_error = bool(result.isError)
        except Exception as exc:  # erreur côté serveur -> on la remonte à Claude
            text, is_error = f"Erreur: {exc}", True
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": text,
                "is_error": is_error,
            }
        )
    messages.append({"role": "user", "content": tool_results})


async def ask_claude(client, session, messages, anthropic_tools):
    """Boucle agentique : on tourne tant que Claude demande des tools."""
    while True:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=(
                "Tu es un assistant de gestion documentaire. "
                "Utilise les tools fournis pour lire ou modifier les documents."
            ),
            tools=anthropic_tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        await handle_tool_calls(session, response, messages)


async def main(demo: bool) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY n'est pas définie.")
        print("   Ce client a besoin de l'API pour parler à Claude.")
        print("   Sans clé, utilise plutôt : python test_server.py\n")
        return

    client = AsyncAnthropic()
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1) TOOLS exposés à Claude
            tools = (await session.list_tools()).tools
            anthropic_tools = mcp_tools_to_anthropic(tools)

            # 2) RESOURCE DIRECTE : les noms de documents (autocomplete)
            names = (await session.read_resource("docs://documents")).contents[0]
            import json

            doc_names = json.loads(names.text)
            print("📚 Documents disponibles :", ", ".join(doc_names))

            prompts = (await session.list_prompts()).prompts
            print("⚡ Commandes :", ", ".join("/" + p.name for p in prompts))
            print("   Tape @nom_du_doc pour injecter son contenu, 'exit' pour quitter.\n")

            messages: list[dict] = []
            questions = ["Quels documents parlent de revenue, et résume-les ?"] if demo else None

            while True:
                if demo:
                    if not questions:
                        break
                    user_input = questions.pop(0)
                    print(f"Vous: {user_input}")
                else:
                    try:
                        user_input = input("Vous: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        break
                if not user_input:
                    continue
                if user_input.lower() in {"exit", "quit"}:
                    break

                # 3) PROMPT : /format doc_id -> instructions pré-écrites
                if user_input.startswith("/format"):
                    parts = user_input.split()
                    doc_id = parts[1] if len(parts) > 1 else doc_names[0]
                    prompt = await session.get_prompt("format", {"doc_id": doc_id})
                    user_input = prompt.messages[0].content.text

                # 4) RESOURCE TEMPLÉE : @doc -> injection de contexte
                if "@" in user_input:
                    mention = user_input.split("@")[1].split()[0].strip(",.")
                    match = next((n for n in doc_names if n.startswith(mention)), None)
                    if match:
                        content = (
                            await session.read_resource(f"docs://documents/{match}")
                        ).contents[0].text
                        user_input = (
                            f'<document id="{match}">\n{content}\n</document>\n\n'
                            + user_input
                        )
                        print(f"   📄 contenu de {match} injecté dans le prompt")
                    else:
                        print(f"   ⚠️  aucun document ne commence par « {mention} »")

                messages.append({"role": "user", "content": user_input})
                answer = await ask_claude(client, session, messages, anthropic_tools)
                print(f"\nClaude: {answer}\n")


if __name__ == "__main__":
    asyncio.run(main(demo="--demo" in sys.argv))
