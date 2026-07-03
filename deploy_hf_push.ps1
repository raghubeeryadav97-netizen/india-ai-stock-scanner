# Push deploy_bundle to Hugging Face Space (permanent URL)
param(
    [string]$Username = $env:HF_USERNAME,
    [string]$Token = $env:HF_TOKEN,
    [string]$SpaceName = "india-ai-stock-scanner"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Bundle = Join-Path $Root "deploy_bundle"
$Git = "C:\Program Files\Git\cmd\git.exe"
$Work = Join-Path $env:TEMP "hf-space-deploy"

if (-not $Username -or -not $Token) {
    Write-Host "Set credentials first:" -ForegroundColor Yellow
    Write-Host '$env:HF_USERNAME="your_hf_username"'
    Write-Host '$env:HF_TOKEN="hf_xxxxxxxx"   # Write token from https://huggingface.co/settings/tokens'
    Write-Host "Then run: powershell -ExecutionPolicy Bypass -File deploy_hf_push.ps1"
    Start-Process "https://huggingface.co/new-space?sdk=streamlit"
    exit 1
}

if (-not (Test-Path $Bundle)) {
    Write-Error "deploy_bundle missing. Re-run setup."
}

if (Test-Path $Work) { Remove-Item $Work -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Work | Out-Null
Set-Location $Work

$remote = "https://$Username`:$Token@huggingface.co/spaces/$Username/$SpaceName"
& $Git clone $remote repo 2>$null
if (-not (Test-Path "repo")) {
    Write-Host "Creating new Space via API..." -ForegroundColor Cyan
    python -c "from huggingface_hub import create_repo; create_repo('$Username/$SpaceName', repo_type='space', space_sdk='streamlit', private=False, exist_ok=True, token='$Token')"
    & $Git clone $remote repo
}

Copy-Item -Path (Join-Path $Bundle '*') -Destination repo -Recurse -Force
Set-Location repo
& $Git config user.email "deploy@local"
& $Git config user.name "India AI Scanner"
& $Git add .
& $Git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { & $Git commit -m "Deploy India AI Stock Scanner" }
& $Git push

Write-Host ""
Write-Host "PERMANENT LIVE URL:" -ForegroundColor Green
Write-Host "https://$Username-$SpaceName.hf.space"
Write-Host "https://huggingface.co/spaces/$Username/$SpaceName"