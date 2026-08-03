# VIGIBARRAGENS–MT — arranque local (Windows).
# Uso (na raiz do repositório ou em barragens-mt):
#   powershell -ExecutionPolicy Bypass -File .\barragens-mt\rodar_local.ps1
#   powershell -ExecutionPolicy Bypass -File .\rodar_local.ps1

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
Set-Location $Root

Write-Host "== VIGIBARRAGENS local ==" -ForegroundColor Cyan
Write-Host "Pasta: $Root"

$py = $null
foreach ($c in @("py", "python", "python3")) {
  try {
    $v = & $c -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $v) { $py = $c; break }
  } catch {}
}
if (-not $py) {
  throw "Python nao encontrado. Instale Python 3.11+ e tente de novo."
}

Write-Host "Python: $py" -ForegroundColor Green

if (-not (Test-Path ".\.venv")) {
  Write-Host "== criando .venv ==" -ForegroundColor Cyan
  & $py -m venv .venv
}

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  throw "venv incompleto: $venvPy"
}

Write-Host "== dependencias Streamlit ==" -ForegroundColor Cyan
& $venvPy -m pip install -q --upgrade pip
& $venvPy -m pip install -q -r requirements-streamlit.txt

$painel = Join-Path $Root "painel"
if (Test-Path (Join-Path $painel "index.html")) {
  Write-Host "== painel HTML em http://127.0.0.1:8765 ==" -ForegroundColor Cyan
  Start-Process -FilePath $venvPy -ArgumentList @("-m", "http.server", "8765", "--bind", "127.0.0.1") -WorkingDirectory $painel -WindowStyle Minimized
} else {
  Write-Host "Painel HTML nao encontrado em painel/ — so o Streamlit sera aberto." -ForegroundColor Yellow
}

Write-Host "== Streamlit em http://127.0.0.1:8501 ==" -ForegroundColor Green
Write-Host "Ctrl+C para encerrar o Streamlit. Feche a janela do http.server se quiser parar o painel HTML."
& $venvPy -m streamlit run streamlit_app.py --server.port 8501 --server.address 127.0.0.1 --browser.gatherUsageStats false
