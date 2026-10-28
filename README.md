<div align="center">

# MCP — Serveur documentaire

**Un serveur Model Context Protocol complet, et les preuves qu'il fonctionne.**

Tools · Resources · Prompts · Client · Tests · Guide 24 pages

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/mcp-1.30-4f9d69)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#-tester)
[![Guide](https://img.shields.io/badge/guide-24%20pages-d9739b)](docs/MCP-Guide.pdf)

</div>

---

Ce dépôt contient le projet fil rouge du cours
_[Introduction to Model Context Protocol](https://academy.claude.com/courses/introduction-to-model-context-protocol)_
(Claude Academy), reconstruit, corrigé et documenté.

L'objectif n'est pas seulement d'avoir un serveur qui démarre : c'est de **montrer
comment on prouve qu'il fonctionne**, sans modèle, sans clé API, et de documenter les
pièges réels rencontrés en chemin.

> 📘 **Le guide complet (24 pages, PDF)** : [`docs/MCP-Guide.pdf`](docs/MCP-Guide.pdf)
> — architecture, les trois primitives, construction pas à pas, les trois niveaux de
> test, étude de cas illustrée et 14 pièges documentés.

---

## Sommaire

- [Ce que fait le serveur](#-ce-que-fait-le-serveur)
- [Démarrage rapide](#-démarrage-rapide)
- [Tester — les trois niveaux](#-tester--les-trois-niveaux)
- [Les trois primitives expliquées](#-les-trois-primitives-expliquées)
- [Structure du dépôt](#-structure-du-dépôt)
- [Brancher sur Claude Desktop / Claude Code](#-brancher-sur-claude-desktop--claude-code)
- [Pièges connus](#-pièges-connus)
- [Aller plus loin](#-aller-plus-loin)

---

## 🧩 Ce que fait le serveur

Un mini gestionnaire de documents, avec les trois familles de capacités du protocole.

| Élément | Type | Qui décide | Rôle |
|---|---|---|---|
| `read_doc_contents` | **tool** | le modèle | lire un document |
| `edit_document` | **tool** | le modèle | remplacer une chaîne (première occurrence) |
| `search_docs` | **tool** | le modèle | chercher un mot-clé, renvoyer des extraits |
| `docs://documents` | **resource** directe | l'application | liste des ids, en JSON — pour l'autocomplete `@` |
| `docs://documents/{doc_id}` | **resource** templatée | l'application | contenu d'un document, en texte brut |
| `format` | **prompt** | l'utilisateur | instructions de réécriture en markdown |

Les documents sont stockés dans un dictionnaire en mémoire : le serveur repart de son
état initial à chaque redémarrage.

---

## 🚀 Démarrage rapide

### Linux / macOS

```bash
git clone https://github.com/thekiller-dev/mcp-server-course.git
cd mcp-server-course

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Ou avec [uv](https://docs.astral.sh/uv/) :

```bash
uv venv && uv pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Fish (Linux)

```fish
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# ou, pour tout enchaîner d'un coup :
fish setup.fish
```

> ⚠️ **Version du SDK.** Le cours utilise `FastMCP`. Depuis la 2.x, le SDK `mcp` l'a
> renommé `MCPServer` et a changé plusieurs signatures : tout le code ci-dessous casse
> avec `No module named 'mcp.server.fastmcp'`. `requirements.txt` épingle donc
> `mcp[cli]<2`.

---

## 🧪 Tester — les trois niveaux

### Niveau 1 — sans clé API, sans navigateur (3 secondes)

```bash
.venv/bin/python test_server.py
```

Ce script lance le serveur en sous-processus et parle le protocole en stdio, exactement
comme le ferait Claude Desktop. Il vérifie les tools et leurs schémas, appelle un tool,
lit les deux resources, récupère le prompt.

```
✅ connecté à DocumentMCP v1.30.0

TOOLS : read_doc_contents, edit_document, search_docs
RESOURCES : [('docs://documents', 'application/json')]
RESOURCE TEMPLATES : [('docs://documents/{doc_id}', 'text/plain')]
PROMPTS : format

🎉 tous les tests passent
```

### Niveau 2 — la boucle complète, racontée

```bash
.venv/bin/python demo_sans_cle.py
```

Rejoue ce que ferait un modèle, tool call après tool call, en affichant chaque étape :
lecture, édition, vérification de la persistance, **erreur volontaire** (l'exception
revient comme résultat, sans casser la session), lecture des resources, récupération du
prompt.

### Niveau 3 — l'inspecteur

```bash
.venv/bin/mcp dev mcp_server.py     # nécessite Node.js (npx)
```

Le terminal affiche une URL du type `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=…`.
Ouvrez **l'URL complète** — sans le jeton, la connexion est refusée.

À essayer dans l'interface :

| Onglet | Valeur | Ce que ça prouve |
|---|---|---|
| Tools → `read_doc_contents` | `{"document_id": "plan.md"}` | schéma dérivé du code |
| Tools → `edit_document` | old `4. Ship it`, new `4. Ship it to production` | l'état persiste entre deux appels |
| Tools → `edit_document` | old `ce texte n'existe pas` | **une erreur reste une réponse** |
| Resources | `docs://documents` | sérialisation JSON automatique |
| Resource Templates | `docs://documents/{doc_id}` + `report.pdf` | parsing du gabarit d'URI |
| Prompts | `format` + `email.md` | prompt calculé côté serveur |

Panneau de droite, onglet **Protocol** : chaque ligne est un message JSON-RPC réel.

### Niveau 4 — un modèle aux commandes

```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # PowerShell : $env:ANTHROPIC_API_KEY = "..."
.venv/bin/python mcp_client.py
```

Trois questions suffisent à valider le découpage :

| Question | Ce qui doit se passer | Primitive |
|---|---|---|
| `Quels documents parlent de revenue ?` | Claude appelle `search_docs` seul | tool |
| `@report.pdf résume les chiffres` | **aucun** tool call, contenu injecté | resource |
| `/format email.md` | instructions récupérées puis envoyées | prompt |

La deuxième ligne est la plus importante : un tool call là où une resource suffit
signale une architecture mal découpée.

---

## 🧠 Les trois primitives expliquées

La différence n'est pas technique, elle tient à **qui décide**.

```
Ça lit des données                        → resource   (l'application décide)
Ça agit, ou ça peut échouer               → tool       (le modèle décide)
C'est une consigne destinée au modèle     → prompt     (l'utilisateur décide)
```

### Un tool : le schéma vient du code

```python
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
```

- le type hint `str` devient `"type": "string"` dans le JSON Schema ;
- `Field(description=…)` devient la description du paramètre — c'est du **prompt
  engineering**, pas de la décoration ;
- `raise ValueError` devient un **résultat d'erreur** renvoyé au modèle, pas un crash.

Vous n'écrivez jamais de schéma JSON à la main : il ne peut donc pas dériver de
l'implémentation.

### Une resource : directe ou templatée

```python
@mcp.resource("docs://documents", mime_type="application/json")
def list_docs() -> list[str]:
    return list(docs.keys())

@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
def fetch_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    return docs[doc_id]
```

Le préfixe d'URI est libre : ce n'est pas une URL réseau, c'est un espace de noms. Le SDK
extrait `{doc_id}` et le passe en argument nommé.

### Un prompt : la couche utilisateur

```python
@mcp.prompt(name="format", description="Rewrite the document as clean markdown.")
def format_document(doc_id: str = Field(description="Id of the document")) -> str:
    return f"""Please rewrite the following document into clean markdown.
Do not invent information.

<document id="{doc_id}">
{docs.get(doc_id, "Document not found")}
</document>"""
```

---

## 📁 Structure du dépôt

```
mcp-server-course/
├── mcp_server.py            # le serveur : 3 tools, 2 resources, 1 prompt
├── mcp_client.py            # client + boucle agentique avec Claude (@mention, /format)
├── test_server.py           # test de protocole — aucune clé API requise
├── demo_sans_cle.py         # la boucle complète, rejouée et commentée
├── requirements.txt         # mcp[cli]<2, anthropic
├── pyproject.toml           # [tool.uv] package = false (voir « Pièges connus »)
├── setup.fish               # installation + test en une commande (fish)
└── docs/
    ├── MCP-Guide.pdf        # le guide de 24 pages
    └── screenshots/         # preuves d'exécution (inspecteur, JSON-RPC)
```

---

## 🔌 Brancher sur Claude Desktop / Claude Code

**Claude Desktop** — `claude_desktop_config.json` :

| OS | Chemin |
|---|---|
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "documents": {
      "command": "uv",
      "args": ["--no-project", "--with", "mcp", "mcp", "run",
               "/chemin/absolu/vers/mcp-server-course/mcp_server.py"]
    }
  }
}
```

Quittez **complètement** l'application puis relancez-la : la configuration n'est lue
qu'au démarrage.

**Claude Code** :

```bash
claude mcp add documents -- python /chemin/absolu/vers/mcp_server.py
```

---

## ⚠️ Pièges connus

Ces erreurs sont documentées parce qu'elles ont réellement été rencontrées.

| Symptôme | Cause | Solution |
|---|---|---|
| `command not found: uv` | binaire dans `~/.local/bin`, absent du PATH | `fish_add_path ~/.local/bin` |
| `syntax error: unexpected end of file` | chemin abîmé par un copier-coller (`[env.fish](http://…)`) | retaper la commande |
| `No module named 'mcp'` | Python du système au lieu du venv | `.venv/bin/python test_server.py` |
| `No module named 'mcp.server.fastmcp'` | SDK 2.x, `FastMCP` → `MCPServer` | `pip install "mcp[cli]<2"` |
| `Unable to determine which files to ship inside the wheel` | `uv run` tente de builder le dossier | `[tool.uv] package = false`, ou `uv run --no-project …` |
| terminal figé après `mcp run` | comportement normal du stdio | `mcp dev` pour un humain, `mcp run` pour un client |
| `npx: command not found` | Node.js absent | Node 20+ via NodeSource, pas le `npm` d'apt |
| `nodejs : Conflicts: npm` | nodejs NodeSource + npm d'apt | ne pas installer `npm` via apt |
| inspecteur « Disconnected » | URL sans le jeton | ouvrir le lien complet `?MCP_PROXY_AUTH_TOKEN=…` |
| le modèle ignore l'outil | description trop vague | dire *quand* l'utiliser, pas seulement ce qu'il fait |

**La règle de tri** : (1) le script de test répond-il ? (2) l'inspecteur exécute-t-il
l'outil à la main ? (3) seulement ensuite, regarder les descriptions. 90 % des problèmes
se règlent à l'étape 1.

---

## 🔭 Aller plus loin

1. **Resource de synthèse** — `stats://documents` renvoyant en JSON le nombre de
   documents, le nombre total de mots et le document le plus long.
2. **Tool d'écriture complète** — `create_document(document_id, content)`, avec erreur
   explicite si l'identifiant existe déjà.
3. **Transport HTTP** — `mcp.run(transport="streamable-http")`, connexion avec
   `mcp.client.streamable_http`, puis sortie du mono-utilisateur local.
4. **Persistance** — remplacer le dictionnaire par des fichiers ou une base. La surface
   MCP ne bouge pas : c'est le signe d'une bonne séparation.

---

## 📚 Ressources

- [Introduction to Model Context Protocol](https://academy.claude.com/courses/introduction-to-model-context-protocol) — Claude Academy
- [Spécification MCP](https://modelcontextprotocol.io/specification)
- [SDK Python](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)

---

<div align="center">
<sub>Construit en apprenant · documenté en déboguant · partagé pour que ça serve.</sub>
</div>
