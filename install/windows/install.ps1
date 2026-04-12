# PDF-OCR-Converter — Windows installer
#
# Fully self-contained:
#   - Checks for Python 3.10+ and installs it via winget if missing
#   - Detects and repairs a broken .venv from a previous failed run
#   - Creates a Python venv and installs dependencies
#   - Registers two context menu entries on .pdf:
#       * OCR to DOCX
#       * OCR Settings
#   - Launches the credential setup dialog on first install
#
# Note: "Merge & OCR to DOCX" is Linux/Nemo-only. On Windows, multi-selection
# via Explorer triggers "OCR to DOCX" individually per file.
#
# Run from PowerShell in the project directory:
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

# --- Preflight: Python 3.10+ ---
function Test-PythonOk {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { return $false }
    try {
        $ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $parts = $ver.Split('.')
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        return ($major -gt 3) -or ($major -eq 3 -and $minor -ge 10)
    } catch {
        return $false
    }
}

if (-not (Test-PythonOk)) {
    Write-Host "-> Python 3.10+ not found. Attempting install via winget..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "X winget is not available."
        Write-Host "  Please install Python 3.10+ manually from https://www.python.org/downloads/"
        Write-Host "  IMPORTANT: enable 'Add Python to PATH' during installation."
        exit 1
    }
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    # Refresh PATH for current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Test-PythonOk)) {
        Write-Host "X Python still not detected after winget install."
        Write-Host "  Please close this PowerShell, open a new one, and re-run the installer."
        exit 1
    }
    Write-Host "OK Python installed."
}

# --- Python venv (repair broken venv from previous failed run) ---
if ((Test-Path $VenvDir) -and -not (Test-Path $PythonExe)) {
    Write-Host "-> Removing broken venv from previous run..."
    Remove-Item -Recurse -Force $VenvDir
}
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
