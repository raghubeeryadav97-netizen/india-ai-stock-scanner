@echo off
title Permanent Host Setup
cd /d "%~dp0"
echo.
echo Choose permanent hosting:
echo   1 = Streamlit Cloud (GitHub)  [RECOMMENDED]
echo   2 = Hugging Face Spaces
echo.
set /p choice=Enter 1 or 2: 
if "%choice%"=="1" (
  powershell -ExecutionPolicy Bypass -File "%~dp0deploy_permanent_github.ps1"
) else if "%choice%"=="2" (
  echo.
  echo 1) https://huggingface.co/join  (free account)
  echo 2) https://huggingface.co/settings/tokens  (Write token)
  echo 3) PowerShell mein run karo:
  echo    set HF_TOKEN=hf_your_token_here
  echo    python deploy_permanent_hf.py
  echo.
  start https://huggingface.co/settings/tokens
  pause
) else (
  echo Invalid choice
  pause
)