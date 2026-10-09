@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0tools\bootstrap.cmd" build-all
exit /b %ERRORLEVEL%
