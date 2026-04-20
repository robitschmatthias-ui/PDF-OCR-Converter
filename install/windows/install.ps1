# PDF-OCR-Converter - Windows installer
#
# Fully self-contained:
#   - Checks for Python 3.10+ and installs it via winget if missing
#   - Detects and repairs a broken .venv from a previous failed run
#   - Creates a Python venv and installs dependencies
#   - Registers two context menu entries on .pdf:
#       * OCR to DOCX
#       * OCR Settings
#   - Launches the credential setup dialog on first install
#   - Shows a live spinner during long-running steps
#
# Note: "Merge & OCR to DOCX" is Linux/Nemo-only. On Windows, multi-selection
# via Explorer triggers "OCR to DOCX" individually per file.
#
# Run from PowerShell in the project directory:
#   .\install\windows\install.ps1

$ErrorActionPreference = "Stop"

$ProjectDir       = (Resolve-Path "$PSScriptRoot\..\..").Path
$VenvDir          = Join-Path $ProjectDir ".venv"
$PythonExe        = Join-Path $VenvDir "Scripts\python.exe"
$PythonwExe       = Join-Path $VenvDir "Scripts\pythonw.exe"
$RequirementsFile = Join-Path $ProjectDir "requirements.txt"

Write-Host "PDF-OCR-Converter Installer (Windows)"
Write-Host "======================================"
Write-Host "Projektverzeichnis: $ProjectDir"
Write-Host ""

# --- Spinner helper ---
# Runs $Exe with $Arguments, animates a spinner while the process runs,
# and exits the installer with an error message if the process fails.
function Invoke-Step {
    param(
        [string]   $Label,
        [string]   $Exe,
        [string[]] $Arguments = @()
    )
    $frames  = @('/', '-', '\', '|')
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()

    $proc = Start-Process -FilePath $Exe -ArgumentList $Arguments `
        -RedirectStandardOutput $outFile -RedirectStandardError $errFile `
        -NoNewWindow -PassThru

    $i = 0
    while (-not $proc.HasExited) {
        Write-Host -NoNewline "`r[$($frames[$i % 4])] $Label ..."
        $i++
        Start-Sleep -Milliseconds 120
    }
    $proc.WaitForExit()

    if ($proc.ExitCode -ne 0) {
        Write-Host "`r[X] $Label                              "
        Get-Content $errFile | ForEach-Object { Write-Host "    $_" }
        Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue
        exit 1
    }
    Write-Host "`r[+] $Label                              "
    Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue
}

# --- Preflight: Python 3.10+ ---
# Prefer the 'py' launcher; skip the Microsoft Store stub at WindowsApps\python.exe
# which hangs the shell while opening the Store in a hidden background window.
$Script:PythonCmd = $null

function Test-PythonOk {
    foreach ($candidate in @(@("py", "-3"), @("python"))) {
        $cmd = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($cmd.Source -and $cmd.Source -like "*\WindowsApps\*") { continue }
        try {
            $ver = & $candidate[0] $candidate[1..($candidate.Length-1)] -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            $parts = $ver.Split('.')
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if (($major -gt 3) -or ($major -eq 3 -and $minor -ge 10)) {
                $Script:PythonCmd = $candidate
                return $true
            }
        } catch { }
    }
    return $false
}

if (Test-PythonOk) {
    Write-Host "[+] Python gefunden ($($Script:PythonCmd -join ' '))"
} else {
    Write-Host "[>] Python 3.10+ nicht gefunden. Installation via winget..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "[X] winget nicht verfuegbar."
        Write-Host "    Bitte Python 3.10+ manuell installieren: https://www.python.org/downloads/"
        Write-Host "    WICHTIG: 'Add Python to PATH' aktivieren."
        exit 1
    }
    Write-Host "    (Das kann eine Minute dauern - winget laedt Python herunter...)"
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    Write-Host "[+] Python installiert. Installer wird in neuer Session fortgesetzt..."
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Wait
    exit 0
}

# --- Python venv ---
if ((Test-Path $VenvDir) -and -not (Test-Path $PythonExe)) {
    Write-Host "[>] Defektes venv aus vorherigem Lauf wird entfernt..."
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $VenvDir)) {
    $pyExec = $Script:PythonCmd[0]
    $pyArgs = if ($Script:PythonCmd.Length -gt 1) {
        $Script:PythonCmd[1..($Script:PythonCmd.Length - 1)] + @("-m", "venv", $VenvDir)
    } else {
        @("-m", "venv", $VenvDir)
    }
    Invoke-Step "Python venv wird erstellt" $pyExec $pyArgs
} else {
    Write-Host "[+] Python venv vorhanden"
}

Invoke-Step "pip wird aktualisiert" `
    $PythonExe @("-m", "pip", "install", "--quiet", "--upgrade", "pip")

Invoke-Step "Python-Abhaengigkeiten werden installiert (kann einen Moment dauern)" `
    $PythonExe @("-m", "pip", "install", "--quiet", "-r", $RequirementsFile)

# --- Register context menu entries ---
$OcrScript      = Join-Path $ProjectDir "src\ocr_convert.py"
$SettingsScript = Join-Path $ProjectDir "src\setup_credentials.py"
$IconFile       = Join-Path $ProjectDir "pdf-ocr-icon.ico"
$OcrCmd         = "`"$PythonwExe`" `"$OcrScript`" `"%1`""
$SettingsCmd    = "`"$PythonwExe`" `"$SettingsScript`""
$RegRoot        = "HKCU:\Software\Classes\SystemFileAssociations\.pdf\shell"

New-Item -Path "$RegRoot\OCR to DOCX\command"  -Force | Out-Null
Set-ItemProperty -Path "$RegRoot\OCR to DOCX"          -Name "(default)" -Value "OCR to DOCX"
Set-ItemProperty -Path "$RegRoot\OCR to DOCX"          -Name "Icon"      -Value $IconFile
Set-ItemProperty -Path "$RegRoot\OCR to DOCX\command"  -Name "(default)" -Value $OcrCmd

New-Item -Path "$RegRoot\OCR Settings\command" -Force | Out-Null
Set-ItemProperty -Path "$RegRoot\OCR Settings"         -Name "(default)" -Value "OCR Settings"
Set-ItemProperty -Path "$RegRoot\OCR Settings"         -Name "Icon"      -Value $IconFile
Set-ItemProperty -Path "$RegRoot\OCR Settings\command" -Name "(default)" -Value $SettingsCmd

Write-Host "[+] Kontextmenue-Eintraege registriert"

# --- First-run credential setup ---
$ConfigFile = Join-Path $env:APPDATA "pdf-ocr-converter\.env"
if (-not (Test-Path $ConfigFile)) {
    Write-Host "[>] Noch keine Zugangsdaten konfiguriert. Setup-Dialog wird gestartet..."
    & $PythonExe $SettingsScript
}

Write-Host ""
Write-Host "[+] Installation abgeschlossen."
Write-Host "    Rechtsklick auf eine PDF-Datei > 'OCR to DOCX' oder 'OCR Settings'."
Write-Host "    (Windows 11: ggf. erst 'Weitere Optionen anzeigen' klicken)"
