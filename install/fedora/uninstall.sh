#!/usr/bin/env bash
# Uninstaller: removes the GNOME Files (Nautilus) extension.
# Does NOT remove the project dir, the venv, or stored credentials
# (~/.config/pdf-ocr-converter/).
set -euo pipefail

EXT_DIR="${HOME}/.local/share/nautilus-python/extensions"
EXT_NAME="pdf_ocr_converter.py"
target="${EXT_DIR}/${EXT_NAME}"

if [ -f "${target}" ]; then
    rm -v "${target}"
    # Drop the compiled cache too, if present
    rm -f "${EXT_DIR}/__pycache__/${EXT_NAME%.py}."*.pyc 2>/dev/null || true
else
    echo "Extension not installed at ${target} (nothing to remove)."
fi

# Reload Nautilus so the menu entries disappear
if command -v nautilus >/dev/null 2>&1; then
    nautilus -q >/dev/null 2>&1 || true
fi

echo
echo "✓ Nautilus extension removed."
echo "Credentials at ~/.config/pdf-ocr-converter/ were NOT touched."
echo "The project directory and its .venv were NOT removed."
