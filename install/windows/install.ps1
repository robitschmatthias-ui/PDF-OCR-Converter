# PDF-OCR-Converter — Windows installer
#
# - Creates a Python venv in the project dir
# - Installs dependencies from requirements.txt
# - Registers two context menu entries on .pdf:
#     * OCR to DOCX
#     * OCR Settings
# - Launches the credential setup dialog on first install
#
# Note: The "Merge & OCR to DOCX" action is Linux/Nemo-only. On Windows,
# multi-selection via Explorer triggers "OCR to DOCX" individually per file.
#
# Run from an elevated PowerShell in the project directory:
#   .\install\windows\install.ps1

$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
$VenvDir = Join-Path $ProjectDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$PythonwExe = Join-Path $VenvDir "Scripts\pythonw.exe"

Write-Host "PDF-OCR-Converter Installer (Windows)"
Write-Host "======================================"
Write-Host "Project dir: $ProjectDir"
Write-Host ""

# --- Python venv ---
if (-not (Test-Path $VenvDir)) {
    Write-Host "-> Creating Python venv..."
    python -m venv $VenvDir
}
Write-Host "-> Installing Python dependencies..."
& $PythonExe -m pip install --quiet --upgrade pip
& $PythonExe -m pip install --quiet -r (Join-Path $ProjectDir "requirements.txt")

# --- Register context menu entries ---
$OcrScript = Join-Path $ProjectDir "src\ocr_convert.py"
$SettingsScript = Join-Path $ProjectDir "src\setup_credentials.py"

$OcrCmd      = "`"$PythonwExe`" `"$OcrScript`" `"%1`""
$SettingsCmd = "`"$PythonwExe`" `"$SettingsScript`""

$RegRoot = "HKCU:\Software\Classes\SystemFileAssociations\.pdf\shell"

New-Item -Path "$RegRoot\OCR to DOCX\command"  -Force | Out-Null
Set-ItemProperty -Path "$RegRoot\OCR to DOCX"            -Name "(default)" -Value "OCR to DOCX"
Set-ItemProperty -Path "$RegRoot\OCR to DOCX\command"    -Name "(default)" -Value $OcrCmd

New-Item -Path "$RegRoot\OCR Settings\command" -Force | Out-Null
Set-ItemProperty -Path "$RegRoot\OCR Settings"           -Name "(default)" -Value "OCR Settings"
Set-ItemProperty -Path "$RegRoot\OCR Settings\command"   -Name "(default)" -Value $SettingsCmd

Write-Host "-> Context menu entries registered."

# --- First-run credential setup ---
$ConfigFile = Join-Path $env:APPDATA "pdf-ocr-converter\.env"
if (-not (Test-Path $ConfigFile)) {
    Write-Host "-> No credentials configured yet. Launching setup dialog..."
    & $PythonExe $SettingsScript
}

Write-Host ""
Write-Host "Installation complete."
Write-Host "Right-click a PDF in Explorer to use 'OCR to DOCX' or 'OCR Settings'."
Write-Host "(On Windows 11: click 'Show more options' to see the classic menu.)"
