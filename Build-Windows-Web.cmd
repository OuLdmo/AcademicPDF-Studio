@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0tools\bootstrap.cmd" build-web
exit /b %ERRORLEVEL%
