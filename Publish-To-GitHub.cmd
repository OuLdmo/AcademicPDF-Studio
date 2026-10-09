@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto fail
where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed. Install Git for Windows and try again.
  echo https://git-scm.com/downloads/win
  goto fail
)
echo.
echo Target repository: https://github.com/OuLdmo/AcademicPDF-Studio
echo Make sure this EMPTY GitHub repository already exists under your account.
echo Review files before publishing. NEVER publish API keys or private PDFs.
echo.
choice /C YN /N /M "Continue with upload? [Y/N] "
if errorlevel 2 exit /b 0
if not exist .git\HEAD (
  git init -b main
  if errorlevel 1 goto fail
)
git add -A
if errorlevel 1 goto fail
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Initial import: AcademicPDF Studio v0.4.1"
  if errorlevel 1 (
    echo [ERROR] Commit failed. Set git config user.name and user.email.
    goto fail
  )
)
git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin "https://github.com/OuLdmo/AcademicPDF-Studio.git"
  if errorlevel 1 goto fail
)
for /f "delims=" %%R in ('git remote get-url origin') do (
  if /I not "%%R"=="https://github.com/OuLdmo/AcademicPDF-Studio.git" (
    echo [ERROR] Existing git origin does not match the expected repository.
    goto fail
  )
)
git push -u origin main
if errorlevel 1 (
  echo [ERROR] Push failed. Confirm the GitHub repository exists and Git login works.
  goto fail
)
echo [SUCCESS] Project pushed to GitHub.
exit /b 0
:fail
echo.
echo See GITHUB_PUBLISH.md for detailed publishing steps.
pause
exit /b 1
