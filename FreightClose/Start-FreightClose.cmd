@echo off
setlocal
cd /d "%~dp0"
if not exist offline_server.py (
  echo Extract the entire ZIP before running Start-FreightClose.
  pause
  exit /b 1
)
set "FC_BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%FC_BUNDLED%" (
  "%FC_BUNDLED%" offline_server.py --port 0 --open-browser
  goto finished
)
py -3 -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 (
  py -3 offline_server.py --port 0 --open-browser
  goto finished
)
python -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 (
  python offline_server.py --port 0 --open-browser
  goto finished
)
echo Install Python 3.11 or later, then run this launcher again.
:finished
pause
