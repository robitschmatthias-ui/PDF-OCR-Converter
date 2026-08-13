#!/usr/bin/env bash
# Wrapper: activates the project venv and runs merge_and_ocr.py.
# Self-locating: works from wherever the repo is checked out.
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/../.." && pwd )"
VENV="${PROJECT_DIR}/.venv"
SCRIPT="${PROJECT_DIR}/src/merge_and_ocr.py"

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
exec python "${SCRIPT}" "$@"
