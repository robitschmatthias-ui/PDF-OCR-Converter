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
#   - Shows a live spinner during long-running steps
#
# Usage: bash install/linux/install.sh

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/../.." && pwd )"
NEMO_ACTIONS_DIR="${HOME}/.local/share/nemo/actions"

printf 'PDF-OCR-Converter Installer\n'
printf '============================\n'
printf 'Projektverzeichnis: %s\n' "${PROJECT_DIR}"
printf 'Nemo-Aktionen:      %s\n' "${NEMO_ACTIONS_DIR}"
printf '\n'

# --- Spinner helper ---
# Usage: _spin "Label text" command [args...]
# Runs the command in the background and animates a Braille spinner until it
# finishes. On failure, prints the captured output and exits the installer.
_spin() {
    local msg="$1"; shift
    local frames=('⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏' '⠋' '⠙' '⠹')
    local log_file
    log_file="$(mktemp /tmp/pdf-ocr-install.XXXXXX)"
    local i=0

    "$@" >"$log_file" 2>&1 &
    local pid=$!

    while kill -0 "$pid" 2>/dev/null; do
        printf '\r[%s] %s ...' "${frames[$((i % 10))]}" "$msg"
        i=$((i + 1))
        sleep 0.12
    done

    local rc=0
    wait "$pid" || rc=$?
    if [ $rc -ne 0 ]; then
        printf '\r\033[K[✗] %s\n' "$msg"
        sed 's/^/    /' "$log_file"
        rm -f "$log_file"
        exit 1
    fi
    printf '\r\033[K[✓] %s\n' "$msg"
    rm -f "$log_file"
}

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

    # python3-dbus needed for reliable desktop notifications via plyer
    if ! dpkg -s python3-dbus >/dev/null 2>&1; then
        missing+=("python3-dbus")
    fi

    if [ ${#missing[@]} -eq 0 ]; then
        printf '[✓] Systempakete vorhanden\n'
        return 0
    fi

    printf '[→] Fehlende Pakete: %s\n' "${missing[*]}"
    if ! command -v apt-get >/dev/null 2>&1; then
        printf '[✗] apt nicht gefunden. Bitte manuell installieren: %s\n' "${missing[*]}"
        exit 1
    fi

    printf '[→] Installation via apt (sudo-Passwort wird ggf. abgefragt)...\n'
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing[@]}"

    for pkg in "${missing[@]}"; do
        case "$pkg" in
            python3-tk)
                python3 -c "import tkinter" >/dev/null 2>&1 \
                    || { printf '[✗] tkinter fehlt noch nach der Installation\n'; exit 1; } ;;
            python*-venv)
                python3 -c "import ensurepip" >/dev/null 2>&1 \
                    || { printf '[✗] venv fehlt noch nach der Installation\n'; exit 1; } ;;
        esac
    done
    printf '[✓] Systempakete installiert\n'
}
install_system_packages

# --- Python venv ---
VENV_DIR="${PROJECT_DIR}/.venv"
if [ -d "${VENV_DIR}" ] && [ ! -f "${VENV_DIR}/bin/activate" ]; then
    printf '[→] Defektes venv aus vorherigem Lauf wird entfernt...\n'
    rm -rf "${VENV_DIR}"
fi

if [ ! -d "${VENV_DIR}" ]; then
    _spin "Python venv wird erstellt" python3 -m venv "${VENV_DIR}"
else
    printf '[✓] Python venv vorhanden\n'
fi

_spin "pip wird aktualisiert" \
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip

_spin "Python-Abhaengigkeiten werden installiert (kann einen Moment dauern)" \
    "${VENV_DIR}/bin/pip" install --quiet -r "${PROJECT_DIR}/requirements.txt"

# --- Make wrappers executable ---
chmod +x "${SCRIPT_DIR}"/*.sh

# --- Install .nemo_action files ---
mkdir -p "${NEMO_ACTIONS_DIR}"
for action in "${SCRIPT_DIR}"/*.nemo_action; do
    dest="${NEMO_ACTIONS_DIR}/$(basename "${action}")"
    sed "s|__PROJECT_DIR__|${PROJECT_DIR}|g" "${action}" > "${dest}"
done
printf '[✓] Nemo-Aktionen registriert\n'

printf '\n[✓] Installation abgeschlossen.\n\n'

CONFIG_FILE="${HOME}/.config/pdf-ocr-converter/.env"
if [ ! -f "${CONFIG_FILE}" ]; then
    printf '[→] Noch keine Zugangsdaten konfiguriert. Setup-Dialog wird gestartet...\n'
    "${SCRIPT_DIR}/setup_credentials.sh" || true
fi

printf '\nRechtsklick auf eine PDF-Datei in Nemo:\n'
printf '  \xe2\x80\xa2 OCR to DOCX\n'
printf '  \xe2\x80\xa2 Merge & OCR to DOCX  (bei Mehrfachauswahl)\n'
printf '  \xe2\x80\xa2 OCR Settings\n'
