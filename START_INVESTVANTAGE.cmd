@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-InvestVantage.ps1"
if errorlevel 1 (
  echo.
  echo InvestVantage failed to start. Review the message above.
  pause
  exit /b 1
)
endlocal
