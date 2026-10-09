@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0tools\bootstrap.cmd" doctor
exit /b %ERRORLEVEL%
