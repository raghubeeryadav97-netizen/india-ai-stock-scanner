# Permanent deploy: GitHub + Streamlit Cloud
$ErrorActionPreference = "Stop"
$AppDir = $PSScriptRoot
$Git = "C:\Program Files\Git\cmd\git.exe"

if (-not (Test-Path $Git)) {
    Write-Host "Install Git first: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

Set-Location $AppDir

if (-not (Test-Path ".git")) {
    & $Git init
    & $Git config user.email "deploy@local"
    & $Git config user.name "India AI Scanner"
}

& $Git add streamlit_app.py india_ai_stock_scanner_streamlit.py requirements.txt .streamlit/config.toml artifacts/saved_ai_stock_analysis.json README.md packages.txt render.yaml .gitignore
& $Git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    & $Git commit -m "Update India AI Stock Scanner deploy"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " PERMANENT HOST - STREAMLIT CLOUD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "STEP 1: GitHub repo banao (free)" -ForegroundColor Yellow
Write-Host "  -> https://github.com/new"
Write-Host "  -> Repo name: india-ai-stock-scanner"
Write-Host "  -> Public repo"
Write-Host ""
Write-Host "STEP 2: Neeche wala command chalao (apna USERNAME daalo):" -ForegroundColor Yellow
Write-Host "  git remote add origin https://github.com/YOUR_USERNAME/india-ai-stock-scanner.git"
Write-Host "  git branch -M main"
Write-Host "  git push -u origin main"
Write-Host ""
Write-Host "STEP 3: Streamlit Cloud deploy:" -ForegroundColor Yellow
Write-Host "  -> https://share.streamlit.io"
Write-Host "  -> Sign in with GitHub"
Write-Host "  -> New app"
Write-Host "  -> Main file: streamlit_app.py"
Write-Host "  -> Deploy"
Write-Host ""
Write-Host "Permanent URL milega: https://YOUR_APP.streamlit.app" -ForegroundColor Green
Write-Host ""

$open = Read-Host "GitHub new repo page browser mein kholun? (y/n)"
if ($open -eq 'y') {
    Start-Process "https://github.com/new"
    Start-Sleep 2
    Start-Process "https://share.streamlit.io"
}