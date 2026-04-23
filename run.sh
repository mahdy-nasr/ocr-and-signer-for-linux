#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
VENV=.venv
STAMP="$VENV/.deps-stamp"

if ! command -v tesseract >/dev/null 2>&1; then
    echo "error: tesseract not found on PATH." >&2
    echo "install it with: sudo apt install tesseract-ocr tesseract-ocr-eng" >&2
    exit 1
fi

if ! "$PY" -c "import venv" >/dev/null 2>&1; then
    echo "error: Python venv module not available." >&2
    echo "install it with: sudo apt install python3-venv" >&2
    exit 1
fi

if [ ! -d "$VENV" ]; then
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip wheel >/dev/null
    "$VENV/bin/pip" install -r requirements.txt
    touch "$STAMP"
elif [ requirements.txt -nt "$STAMP" ]; then
    "$VENV/bin/pip" install -r requirements.txt
    touch "$STAMP"
fi

export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV/bin/python" -m preview_app "$@"
