#!/usr/bin/env bash
# Installer for PDF-OCR-Converter (Linux / Nemo)
#
# Fully self-contained:
#   - Checks required system packages and installs them via apt if missing
#     (asks for sudo password once)
#   - Detects and repairs a broken .venv from a previous failed run
#   - Creates a Python venv and installs Python dependencies
#   - Installs .nemo_action files to ~/.local/share/nemo/actions/
#   - Launches the credential setup dialog on first install
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
install_system_packages() {
    local missing=()

    if ! command -v python3 >/dev/null 2>&1; then
        missing+=("python3")
    fi

    if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
        local py_ver
        py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")"
        missing+=("python${py_ver}-venv")
    fi

    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        missing+=("python3-tk")
    fi

    # python3-dbus (needed for reliable desktop notifications via plyer)
    if ! dpkg -s python3-dbus >/dev/null 2>&1; then
        missing+=("python3-dbus")
    fi

    if [ ${#missing[@]} -eq 0 ]; then
        return 0
    fi

    echo "→ Missing system packages: ${missing[*]}"
    if ! command -v apt >/dev/null 2>&1; then
        echo "✗ This installer uses 'apt' to install system packages."
        echo "  Please install these packages manually: ${missing[*]}"
        exit 1
    fi

    echo "→ Installing via apt (sudo password may be required)..."
    sudo apt update
    sudo apt install -y "${missing[@]}"

    # Verify after install
    for pkg in "${missing[@]}"; do
        case "$pkg" in
            python3-tk)
                python3 -c "import tkinter" >/dev/null 2>&1 || { echo "✗ tkinter still missing after install"; exit 1; } ;;
            python*-venv)
                python3 -c "import ensurepip" >/dev/null 2>&1 || { echo "✗ venv still missing after install"; exit 1; } ;;
        esac
    done
    echo "✓ System packages installed."
}
install_system_packages

# --- Python venv (repair broken venv from previous failed run) ---
VENV_DIR="${PROJECT_DIR}/.venv"
if [ -d "${VENV_DIR}" ] && [ ! -f "${VENV_DIR}/bin/activate" ]; then
    echo "→ Removing broken venv from previous run..."
    rm -rf "${VENV_DIR}"
fi

if [ ! -d "${VENV_DIR}" ]; then
    echo "→ Creating Python venv..."
    python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
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
    sed "s|__PROJECT_DIR__|${PROJECT_DIR}|g" "${action}" > "${dest}"
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
