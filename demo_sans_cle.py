"""
Demo "agent" SANS cle API : rejoue exactement ce que ferait Claude,
tool call apres tool call, en affichant chaque etape du protocole.

    .venv/bin/python demo_sans_cle.py

Prouve que la boucle complete fonctionne : tools serialises, appels,
resultats, erreurs, resources lues, prompt recupere.
"""

import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("mcp_server.py")


def say(role: str, text: str) -> None:
    print(f"\n\033[1m{role}\033[0m {text}")


async def call(session, name, args):
    res = await session.call_tool(name, args)
    txt = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
    flag = "\033[31mERREUR\033[0m" if res.isError else "\033[32mOK\033[0m"
    print(f"   -> [{flag}] {txt[:160]}")
    return txt


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            info = await s.initialize()
            say("SERVEUR", f"{info.serverInfo.name} — protocole {info.protocolVersion}")

            # ---- Ce que fait le CLIENT au demarrage ----
            say("CLIENT", "list_tools() -> le client publie ces tools au modele")
            for t in (await s.list_tools()).tools:
                print(f"   • {t.name}")

            # ---- Tour 1 : l'utilisateur pose une question ----
            say("USER", "Que dit le rapport sur le budget marketing ?")
            say("CLAUDE", "Je dois lire report.pdf -> edit_document/read_doc_contents")
            say("OUTIL", "read_doc_contents(document_id='report.pdf')")
            contenu = await call(s, "read_doc_contents", {"document_id": "report.pdf"})
            say("CLAUDE", "Le rapport recommande de doubler le budget marketing au Q4.")

            # ---- Tour 2 : action avec effet de bord ----
            say("USER", "Ajoute une ligne 'Valide par le comite' a la fin du rapport")
            say("OUTIL", "read_doc_contents puis edit_document")
            await call(s, "read_doc_contents", {"document_id": "report.pdf"})
            await call(s, "edit_document", {
                "document_id": "report.pdf",
                "old_string": "for Q4.",
                "new_string": "for Q4.\nValide par le comite.",
            })
            say("CLAUDE", "Document modifie. Je relis pour verifier.")
            apres = await call(s, "read_doc_contents", {"document_id": "report.pdf"})
            assert "Valide par le comite" in apres
            print("   \033[32m✓\033[0m persistance verifiee")

            # ---- Tour 3 : erreur volontaire (le modele se corrige) ----
            say("OUTIL", "edit_document avec un texte qui n'existe pas")
            say("CLAUDE", "(le modele doit recevoir l'erreur et reessayer)")
            await call(s, "edit_document", {
                "document_id": "report.pdf",
                "old_string": "texte qui n'existe pas",
                "new_string": "x",
            })
            say("OUTIL", "l'erreur est renvoyee comme resultat, pas comme crash")

            # ---- Ce que fait l'APPLICATION avec les resources ----
            say("APP", "read_resource('docs://documents') -> autocomplete @")
            await s.read_resource("docs://documents")
            say("APP", "read_resource('docs://documents/{id}') -> injection de contexte")
            await s.read_resource("docs://documents/plan.md")

            # ---- Ce que fait l'UTILISATEUR avec les prompts ----
            say("USER", "/format email.md")
            p = await s.get_prompt("format", {"doc_id": "email.md"})
            say("PROMPT", p.messages[0].content.text[:100].replace("\n", " ") + " ...")

    print("\n\033[32mBoucle complete validee.\033[0m Les 3 primitives ont ete exercees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(anyio.run(main))
