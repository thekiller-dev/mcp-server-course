#!/usr/bin/env fish
# Setup + test du serveur MCP, pour Linux + fish.
# Usage :  fish setup.fish
# À lancer depuis le dossier mcp-cours (là où se trouve mcp_server.py).

echo "== 1. PATH (uv) =="
if not contains ~/.local/bin $PATH
    fish_add_path ~/.local/bin
end
# au cas où le shell courant n'aurait pas encore rechargé
set -gx PATH ~/.local/bin $PATH

if not command -q uv
    echo "ERREUR : uv introuvable dans ~/.local/bin"
    echo "Relance : curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
end
uv --version

echo ""
echo "== 2. environnement virtuel =="
if not test -d .venv
    uv venv
end

echo ""
echo "== 3. dependances =="
uv pip install -r requirements.txt

echo ""
echo "== 4. test du serveur =="
.venv/bin/python test_server.py
