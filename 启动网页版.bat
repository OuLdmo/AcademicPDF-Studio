@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot open software directory. Unzip all files first.
  pause
  exit /b 1
)
if exist "dist\AcademicPDF-Web\AcademicPDF-Web.exe" (
  "dist\AcademicPDF-Web\AcademicPDF-Web.exe" --self-test >nul 2>nul
  if not errorlevel 1 (
    echo Starting prebuilt Windows application...
    "dist\AcademicPDF-Web\AcademicPDF-Web.exe"
    if not errorlevel 1 (
      popd
      exit /b 0
    )
    echo [WARN] EXE could not start. Trying the Python edition...
  )
)
popd
call "%~dp0tools\bootstrap.cmd" web
exit /b %ERRORLEVEL%
