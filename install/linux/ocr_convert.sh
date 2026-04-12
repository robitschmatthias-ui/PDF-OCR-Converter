#!/usr/bin/env bash
# Wrapper: activates venv and runs ocr_convert.py
set -euo pipefail

INSTALL_DIR="${HOME}/scripts/pdf-ocr-converter"
VENV="${INSTALL_DIR}/.venv"
SCRIPT="${INSTALL_DIR}/src/ocr_convert.py"

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
exec python "${SCRIPT}" "$@"
