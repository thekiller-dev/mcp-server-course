"""
Test automatisé du serveur MCP (sans navigateur, sans clé API).

Il lance mcp_server.py en sous-processus, se connecte en stdio comme le ferait
Claude Desktop, et vérifie tools / resources / prompts.

    python test_server.py
"""

import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("mcp_server.py")


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"✅ connecté à {init.serverInfo.name} v{init.serverInfo.version}\n")

            # ---------- TOOLS ----------
            tools = (await session.list_tools()).tools
            print("TOOLS :", ", ".join(t.name for t in tools))
            for t in tools:
                print(f"   - {t.name}: {t.description}")
                print(f"     schéma: {t.inputSchema}")
            print()

            res = await session.call_tool(
                "read_doc_contents", {"document_id": "plan.md"}
            )
            print("read_doc_contents(plan.md) ->")
            print(res.content[0].text, "\n")

            res = await session.call_tool(
                "edit_document",
                {
                    "document_id": "plan.md",
                    "old_string": "4. Ship it",
                    "new_string": "4. Ship it to production",
                },
            )
            print("edit_document ->", res.content[0].text, "\n")

            res = await session.call_tool("read_doc_contents", {"document_id": "plan.md"})
            assert "Ship it to production" in res.content[0].text
            print("vérification de l'édition OK\n")

            res = await session.call_tool("search_docs", {"keyword": "revenue"})
            print("search_docs(revenue) ->", res.content[0].text, "\n")

            # ---------- RESOURCES ----------
            resources = (await session.list_resources()).resources
            print("RESOURCES :", [(str(r.uri), r.mimeType) for r in resources])

            templates = (await session.list_resource_templates()).resourceTemplates
            print("RESOURCE TEMPLATES :", [(t.uriTemplate, t.mimeType) for t in templates])
            print()

            res = await session.read_resource("docs://documents")
            print("read docs://documents ->", res.contents[0].text, "\n")

            res = await session.read_resource("docs://documents/report.pdf")
            print("read docs://documents/report.pdf ->")
            print(res.contents[0].text[:120], "...\n")

            # ---------- PROMPTS ----------
            prompts = (await session.list_prompts()).prompts
            print("PROMPTS :", ", ".join(p.name for p in prompts))

            prompt = await session.get_prompt("format", {"doc_id": "email.md"})
            print("get_prompt(format, email.md) ->")
            print(prompt.messages[0].content.text[:200], "...\n")

    print("🎉 tous les tests passent")
    return 0


if __name__ == "__main__":
    raise SystemExit(anyio.run(main))
