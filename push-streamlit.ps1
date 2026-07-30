# Commit das Ondas 1–3 e push para o GitHub (Streamlit Cloud).
# Uso: clique direito → Executar com PowerShell, ou:
#   powershell -ExecutionPolicy Bypass -File .\push-streamlit.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== status ==" -ForegroundColor Cyan
git status -sb
git remote -v

Write-Host "== stage ==" -ForegroundColor Cyan
git add barragens-mt/streamlit_app.py barragens-mt/executar.py
git add barragens-mt/st_app/
git add barragens-mt/docs/
git add barragens-mt/painel/
git add barragens-mt/scripts/20_painel_comando.py
git add barragens-mt/scripts/29_despacho_alertas.py
git add barragens-mt/scripts/30_cnes_estadual_scaffold.py
git add barragens-mt/scripts/31_onda3_scaffolds.py
git add barragens-mt/scripts/32_rag_indice_docs.py
git add barragens-mt/dados/tratados/cnes_municipios_alvo_mt.csv
git add barragens-mt/dados/tratados/cnes_estadual_status.json
git add barragens-mt/dados/tratados/pae_manchas_cobertura.csv
git add barragens-mt/dados/tratados/sisagua_captacoes_eixo_esqueleto.csv
git add barragens-mt/dados/tratados/vigipos_linha_base_esqueleto.csv
git add barragens-mt/dados/tratados/rag_docs_indice.json
git add barragens-mt/dados/tratados/despacho_alertas_log.csv
git add barragens-mt/dados/tratados/onda3_dados_status.json
git add barragens-mt/relatorios/cnes_estadual_plano.md
git add barragens-mt/relatorios/onda3_dados_scaffolds.md
if (Test-Path streamlit_app.py) { git add streamlit_app.py }

$status = git status --porcelain
if (-not $status) {
  Write-Host "Nada novo para commitar. Tentando push mesmo assim..." -ForegroundColor Yellow
} else {
  git commit -m @"
Implement Ondas 1–3 no VIGIBARRAGENS: KPIs sanitários, município 360, SITREP, despacho e scaffolds de dados.
"@
}

Write-Host "== push ==" -ForegroundColor Cyan
git push -u origin HEAD

Write-Host "== ok ==" -ForegroundColor Green
git status -sb
git rev-parse --short HEAD
Write-Host "Streamlit Cloud deve redeployar a partir de main (entrypoint: streamlit_app.py / barragens-mt/streamlit_app.py)."
