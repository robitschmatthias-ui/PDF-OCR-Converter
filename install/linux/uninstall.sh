#!/usr/bin/env bash
# Uninstaller: removes Nemo actions. Does NOT remove the project dir or
# stored credentials (~/.config/pdf-ocr-converter/).
set -euo pipefail

NEMO_ACTIONS_DIR="${HOME}/.local/share/nemo/actions"

for name in ocr-to-docx merge-and-ocr-to-docx ocr-settings; do
    target="${NEMO_ACTIONS_DIR}/${name}.nemo_action"
    if [ -f "${target}" ]; then
        rm -v "${target}"
    fi
done

echo
echo "✓ Nemo actions removed."
echo "Credentials at ~/.config/pdf-ocr-converter/ were NOT touched."
echo "Project dir was NOT removed."
