@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0.." >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot open project directory. Extract ZIP before running.
  pause
  exit /b 1
)
set "MODE=%~1"
if not defined MODE set "MODE=web"
set "PYRUN="
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys;sys.exit(0 if sys.version_info >= (3,11) and sys.version_info < (3,14) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYRUN=VENV"
)
if not defined PYRUN (
  py -3.11 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYRUN=py -3.11"
)
if not defined PYRUN (
  py -3.12 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYRUN=py -3.12"
)
if not defined PYRUN (
  py -3.13 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYRUN=py -3.13"
)
if not defined PYRUN (
  python -c "import sys;sys.exit(0 if sys.version_info >= (3,11) and sys.version_info < (3,14) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYRUN=python"
)
if not defined PYRUN (
  echo [ERROR] Python 3.11+ was not found.
  echo Install Python 3.11 x64 from https://www.python.org/downloads/windows/
  echo Enable the Python launcher during installation and restart this script.
  pause
  popd
  exit /b 2
)
set "PYTHONUTF8=1"
if /I "%PYRUN%"=="VENV" (
  ".venv\Scripts\python.exe" "tools\windows_bootstrap.py" --mode "%MODE%"
) else (
  %PYRUN% "tools\windows_bootstrap.py" --mode "%MODE%"
)
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo.
  echo [ERROR] Exit code: %RESULT%
  echo Use the diagnostic script and TROUBLESHOOTING.md to investigate.
  if not defined CI pause
)
if not defined CI (
  if /I "%MODE%"=="build-web" if "%RESULT%"=="0" pause
  if /I "%MODE%"=="build-all" if "%RESULT%"=="0" pause
  if /I "%MODE%"=="doctor" if "%RESULT%"=="0" pause
)
popd
exit /b %RESULT%
