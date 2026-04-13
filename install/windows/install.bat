@echo off
REM PDF-OCR-Converter — Windows installer launcher
REM Bypasses PowerShell ExecutionPolicy restrictions.
REM Double-click or run this file; it launches install.ps1.

setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1"
echo.
pause
