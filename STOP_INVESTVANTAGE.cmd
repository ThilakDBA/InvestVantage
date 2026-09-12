@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Stop-InvestVantage.ps1"
if errorlevel 1 (
  echo.
  echo InvestVantage failed to stop cleanly. Review the message above.
  pause
  exit /b 1
)
endlocal
