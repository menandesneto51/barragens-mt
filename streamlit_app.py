"""Atalho na raiz do repositório para o Streamlit Community Cloud."""

from pathlib import Path
import runpy
import sys

APP = Path(__file__).resolve().parent / "barragens-mt" / "streamlit_app.py"
sys.path.insert(0, str(APP.parent))
runpy.run_path(str(APP), run_name="__main__")
