@echo off
REM PDF-OCR-Converter — Windows uninstaller launcher
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%uninstall.ps1"
echo.
pause
