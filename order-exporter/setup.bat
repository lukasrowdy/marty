@echo off
rem One-time setup: makes a private Python environment in .venv and installs Playwright and openpyxl.
cd /d "%~dp0"
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 or newer was not found.
  echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH", then run setup.bat again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating .venv ...
  py -3 -m venv .venv || (echo Could not create .venv & pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt || (echo Package install failed & pause & exit /b 1)
echo.
echo Setup finished. Next: double-click dry-run.bat to test without logging in.
pause
