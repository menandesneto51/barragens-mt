#!/usr/bin/env bash
# VIGIBARRAGENS–MT — arranque local (Linux/macOS).
# Uso: cd barragens-mt && bash rodar_local.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== VIGIBARRAGENS local =="
echo "Pasta: $ROOT"

PY=python3
command -v "$PY" >/dev/null || PY=python
command -v "$PY" >/dev/null || { echo "Python 3 nao encontrado"; exit 1; }

if [[ ! -d .venv ]]; then
  echo "== criando .venv =="
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -q --upgrade pip
python -m pip install -q -r requirements-streamlit.txt

if [[ -f painel/index.html ]]; then
  echo "== painel HTML em http://127.0.0.1:8765 =="
  (cd painel && python -m http.server 8765 --bind 127.0.0.1) &
  HTTP_PID=$!
  trap 'kill "$HTTP_PID" 2>/dev/null || true' EXIT
fi

echo "== Streamlit em http://127.0.0.1:8501 =="
exec python -m streamlit run streamlit_app.py \
  --server.port 8501 \
  --server.address 127.0.0.1 \
  --browser.gatherUsageStats false
