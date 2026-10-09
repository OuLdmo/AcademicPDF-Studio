@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0tools\bootstrap.cmd" install-argos
if not defined CI pause
exit /b %ERRORLEVEL%
