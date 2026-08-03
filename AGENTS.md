# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is

A single product: **VIGIBARRAGENS–MT**, a Streamlit dashboard (Brazilian Portuguese)
for dam-safety monitoring in Mato Grosso. All application code lives under
`barragens-mt/`. The repo-root `streamlit_app.py` is only a thin shim that runs
`barragens-mt/streamlit_app.py` (used by Streamlit Community Cloud). The root PDFs and
the empty `Projeto VSR/` directory are unrelated document artifacts, not code.

### Running the app (dev)

Run from the repo root:

```bash
python3 -m streamlit run streamlit_app.py --server.port 8501 --server.headless true
```

- Use `python3 -m streamlit` (not the bare `streamlit` command): pip installs the
  `streamlit` console script into `~/.local/bin`, which is not on `PATH` here.
- The treated datasets are committed under `barragens-mt/dados/tratados/`, so the app
  runs **fully offline** — there is no database, cache, queue, or backend API to start.

### Non-obvious gotcha: the "Alertabilidade / despacho" page needs `httpx`

The `Ação → Alertabilidade / despacho` page dynamically loads
`barragens-mt/scripts/29_despacho_alertas.py`, which imports `comum` → `httpx`. `httpx`
is **not** in the Streamlit requirements (`requirements.txt` /
`barragens-mt/requirements-streamlit.txt`); it lives in `barragens-mt/requirements.txt`.
If only the Streamlit requirements are installed, that one page crashes with
`ModuleNotFoundError: No module named 'httpx'` while every other page works. The startup
update script installs both requirement sets so all pages render.

Alert dispatch defaults to **dry-run** (log only). Real Telegram/e-mail sending requires
the `VIGI_TELEGRAM_*` / `VIGI_SMTP_*` env vars (or Streamlit `[vigi]` secrets); without
them the page shows `Credenciais: Telegram=ausente · SMTP=ausente`, which is expected.

### Maps

Folium/Leaflet maps fetch tiles from external CDNs (CartoDB / OpenStreetMap). Tiles need
network egress and can briefly show "Map data not yet available" while loading or when
panning/zooming quickly — this is transient tile loading, not an app error.

### Lint / test / build

- **No test suite** and **no lint config** are committed (no pytest/ruff/flake8/black,
  no `pyproject.toml`, no CI). Do not assume a `make test` / `npm test` equivalent exists.
- The only "build" is regenerating data via the offline pipeline:
  `cd barragens-mt && python executar.py` (or specific stages, e.g.
  `python executar.py 05 06 07`). This calls external Brazilian government APIs and is
  **not** needed to run the dashboard, since treated data is already committed.
