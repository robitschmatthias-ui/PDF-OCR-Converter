#!/usr/bin/env bash
# Installer for PDF-OCR-Converter (Linux / Nemo)
#
# - Creates a Python venv in the project dir
# - Installs dependencies from requirements.txt
# - Copies .nemo_action files to ~/.local/share/nemo/actions/
# - Replaces the <HOME_SCRIPTS/...> placeholder with the actual install path
# - Makes wrapper scripts executable
#
# Usage: bash install/linux/install.sh

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/../.." && pwd )"
NEMO_ACTIONS_DIR="${HOME}/.local/share/nemo/actions"

echo "PDF-OCR-Converter Installer"
echo "============================"
echo "Project dir:   ${PROJECT_DIR}"
echo "Nemo actions:  ${NEMO_ACTIONS_DIR}"
echo

# --- Preflight: required system packages ---
check_system_packages() {
    local missing=()

    # python3
    if ! command -v python3 >/dev/null 2>&1; then
        missing+=("python3")
    fi

    # python3-venv (ensurepip must be available)
    if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
        local py_ver
        py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")"
        missing+=("python${py_ver}-venv")
    fi

    # tkinter (needed for GUI dialogs)
    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        missing+=("python3-tk")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo "✗ Missing system packages: ${missing[*]}"
        echo
        echo "Please install them first:"
        echo "  sudo apt install ${missing[*]}"
        echo
        echo "Then re-run: bash install/linux/install.sh"
        exit 1
    fi
}
check_system_packages

# --- Python venv ---
if [ ! -d "${PROJECT_DIR}/.venv" ]; then
    echo "→ Creating Python venv..."
    python3 -m venv "${PROJECT_DIR}/.venv"
fi
# shellcheck disable=SC1091
source "${PROJECT_DIR}/.venv/bin/activate"
echo "→ Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "${PROJECT_DIR}/requirements.txt"
deactivate

# --- Make wrappers executable ---
chmod +x "${SCRIPT_DIR}"/*.sh

# --- Install .nemo_action files ---
mkdir -p "${NEMO_ACTIONS_DIR}"
for action in "${SCRIPT_DIR}"/*.nemo_action; do
    dest="${NEMO_ACTIONS_DIR}/$(basename "${action}")"
    echo "→ Installing $(basename "${action}")"
    sed "s|<HOME_SCRIPTS/pdf-ocr-converter|${PROJECT_DIR}|g" "${action}" > "${dest}"
done

echo
echo "✓ Installation complete."
echo
CONFIG_FILE="${HOME}/.config/pdf-ocr-converter/.env"
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "→ No credentials configured yet. Launching setup dialog..."
    "${SCRIPT_DIR}/setup_credentials.sh" || true
fi

echo
echo "Right-click a PDF in Nemo to use:"
echo "  • OCR to DOCX"
echo "  • Merge & OCR to DOCX  (when multiple PDFs are selected)"
echo "  • OCR Settings"
