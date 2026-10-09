@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0tools\bootstrap.cmd" gui
exit /b %ERRORLEVEL%
