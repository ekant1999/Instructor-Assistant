#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  "${PYTHON_BIN}" -m venv "${ROOT_DIR}/.venv"
fi

"${ROOT_DIR}/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
"${ROOT_DIR}/.venv/bin/pip" install -r "${ROOT_DIR}/requirements.txt"
"${ROOT_DIR}/.venv/bin/pip" install "git+https://github.com/allenai/olmocr.git"

if [[ ! -f "${ROOT_DIR}/.env" && -f "${ROOT_DIR}/.env.example" ]]; then
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
fi

echo "Workspace ready."
echo "Python: ${ROOT_DIR}/.venv/bin/python"
echo "Next:"
echo "  1. Edit ${ROOT_DIR}/.env"
echo "  2. Ensure pdfinfo and pdftoppm are installed"
echo "  3. Run ${ROOT_DIR}/scripts/benchctl validate"

