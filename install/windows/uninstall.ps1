# PDF-OCR-Converter — Windows uninstaller
#
# Removes only the context menu entries. Credentials at
# %APPDATA%\pdf-ocr-converter\ and the project directory are left intact.

$ErrorActionPreference = "Stop"
$RegRoot = "HKCU:\Software\Classes\SystemFileAssociations\.pdf\shell"

foreach ($name in @("OCR to DOCX", "OCR Settings")) {
    $path = Join-Path $RegRoot $name
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
        Write-Host "Removed: $path"
    }
}
Write-Host "Credentials at %APPDATA%\pdf-ocr-converter\ were NOT touched."
