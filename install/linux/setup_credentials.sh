#!/usr/bin/env bash
# Wrapper: activates venv and opens credential setup dialog
set -euo pipefail

INSTALL_DIR="${HOME}/scripts/pdf-ocr-converter"
VENV="${INSTALL_DIR}/.venv"
SCRIPT="${INSTALL_DIR}/src/setup_credentials.py"

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
exec python "${SCRIPT}"
