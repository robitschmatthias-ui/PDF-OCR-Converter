#!/usr/bin/env bash
# Wrapper: activates venv and runs merge_and_ocr.py
set -euo pipefail

INSTALL_DIR="${HOME}/scripts/pdf-ocr-converter"
VENV="${INSTALL_DIR}/.venv"
SCRIPT="${INSTALL_DIR}/src/merge_and_ocr.py"

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
exec python "${SCRIPT}" "$@"
