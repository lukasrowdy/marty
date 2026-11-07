@echo off
rem Runs the exporter. Any options are passed through, for example:  run.bat --last-week
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe export_orders.py %*
echo.
pause
