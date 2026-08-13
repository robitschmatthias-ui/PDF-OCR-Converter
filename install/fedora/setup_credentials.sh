#!/usr/bin/env bash
# Wrapper: activates the project venv and opens the credential setup dialog.
# Self-locating: works from wherever the repo is checked out.
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/../.." && pwd )"
VENV="${PROJECT_DIR}/.venv"
SCRIPT="${PROJECT_DIR}/src/setup_credentials.py"

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
exec python "${SCRIPT}" "$@"
