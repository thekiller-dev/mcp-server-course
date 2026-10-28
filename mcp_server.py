"""
Serveur MCP du cours "Introduction to Model Context Protocol" (Claude Academy).

Un seul fichier, les 3 primitives du protocole :
  - TOOLS      -> le modèle décide de les appeler (actions : lire, éditer)
  - RESOURCES  -> l'application décide (données read-only : liste + contenu d'un doc)
  - PROMPTS    -> l'utilisateur décide (instructions pré-écrites : /format)

Lancement :
    python mcp_server.py            # transport stdio (ce que fait Claude Desktop / le client)
    mcp dev mcp_server.py           # inspecteur web pour tester à la main
"""

from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Le nom passé ici est celui que le client verra dans l'initialisation.
mcp = FastMCP("DocumentMCP", log_level="ERROR")


# ---------------------------------------------------------------------------
# "Base de données" en mémoire : 4 documents texte.
# Dans un vrai serveur, ce serait un dict + accès disque, une base, une API...
# ---------------------------------------------------------------------------
docs = {
    "deposition.md": (
        "# Deposition of Jane Doe\n\n"
        "On the morning of March 3rd, Jane Doe arrived at the warehouse at 8:15 AM.\n"
        "She stated that she did not see anyone else on the loading dock.\n"
        "The security camera footage contradicts this statement."
    ),
    "report.pdf": (
        "Quarterly Report - Q3\n\n"
        "Revenue grew by 12% compared to the previous quarter.\n"
        "Operating costs remained flat, mainly due to remote work policies.\n"
        "The board recommends doubling the marketing budget for Q4."
    ),
    "plan.md": (
        "# Project Plan\n\n"
        "1. Gather requirements\n"
        "2. Build the MCP server\n"
        "3. Test with the MCP Inspector\n"
        "4. Ship it"
    ),
    "email.md": (
        "Subject: Re: Contract review\n\n"
        "Hi Sam, thanks for the draft. I left two comments on clause 4.\n"
        "Can we review them together on Friday?\n\nBest,\nAlex"
    ),
}


# ===========================================================================
# 1) TOOLS — le modèle décide (model-controlled)
# ===========================================================================
# Les type hints deviennent le JSON Schema, et Field(description=...) devient
# la description du paramètre que le modèle lit pour savoir quoi passer.
# Pas besoin d'écrire le schema à la main : c'est tout l'intérêt du SDK.


@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string.",
)
def read_document(
    document_id: str = Field(description="Id of the document to read"),
) -> str:
    if document_id not in docs:
        raise ValueError(f"Doc with id {document_id} not found")
    return docs[document_id]


@mcp.tool(
    name="edit_document",
    description=(
        "Edit a document by replacing a string in the document's content "
        "with a new string."
    ),
)
def edit_document(
    document_id: str = Field(description="Id of the document that will be edited"),
    old_string: str = Field(
        description="The text to replace. Must match exactly, including whitespace."
    ),
    new_string: str = Field(description="The new text to insert in place of the old text"),
) -> str:
    if document_id not in docs:
        raise ValueError(f"Doc with id {document_id} not found")

    doc = docs[document_id]
    if old_string not in doc:
        raise ValueError(f'Text "{old_string}" not found in document')

    # replace(..., 1) : on ne remplace que la PREMIÈRE occurrence.
    docs[document_id] = doc.replace(old_string, new_string, 1)
    return "Document edited successfully"


# --- Bonus (facultatif, montre un 3e tool un peu plus "intelligent") -------
@mcp.tool(
    name="search_docs",
    description="Search for a keyword across all documents and return matching ids.",
)
def search_docs(keyword: str = Field(description="Keyword to look for")) -> dict[str, str]:
    hits = {}
    for doc_id, content in docs.items():
        if keyword.lower() in content.lower():
            index = content.lower().index(keyword.lower())
            hits[doc_id] = "..." + content[max(0, index - 40) : index + 60] + "..."
    return hits


# ===========================================================================
# 2) RESOURCES — l'application décide (app-controlled), read-only
# ===========================================================================
# Une resource = un handler de GET. Le client demande une URI précise,
# le serveur renvoie les données. Aucun appel de tool par le modèle.


@mcp.resource(
    "docs://documents",
    mime_type="application/json",
)
def list_docs() -> list[str]:
    """Resource DIRECTE : URI statique, pas de paramètre.
    Sert à l'autocomplete quand l'utilisateur tape « @ ». """
    return list(docs.keys())


@mcp.resource(
    "docs://documents/{doc_id}",
    mime_type="text/plain",
)
def fetch_doc(doc_id: str) -> str:
    """Resource TEMPLÉE : le SDK parse {doc_id} dans l'URI et le passe
    en argument nommé. C'est ce qui permet d'injecter le contenu du document
    mentionné directement dans le prompt, sans tool call."""
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    return docs[doc_id]


# ===========================================================================
# 3) PROMPTS — l'utilisateur décide (user-controlled)
# ===========================================================================
# Un prompt = un template d'instructions de haute qualité, réutilisable
# (typiquement exposé comme une slash-command dans le client).


@mcp.prompt(
    name="format",
    description="Rewrites the contents of the document into markdown.",
)
def format_document(
    doc_id: str = Field(description="Id of the document to format"),
) -> str:
    return f"""Please rewrite the following document into clean, well-structured markdown.
Use headings, bullet points and emphasis where it improves readability.
Do not invent information. Return only the rewritten document.

<document id="{doc_id}">
{docs.get(doc_id, "Document not found")}
</document>"""


if __name__ == "__main__":
    # stdio = le transport par défaut, celui qu'utilisent les clients locaux.
    mcp.run()
