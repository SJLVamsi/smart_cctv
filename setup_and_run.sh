#!/bin/bash
# One-command setup + run for macOS. Usage: bash setup_and_run.sh
cd "$(dirname "$0")"
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do command -v $c >/dev/null && PY=$c && break; done
[ -z "$PY" ] && { echo "No python3 found. Install from python.org"; exit 1; }
echo "Using $($PY --version)"
[ -d .venv ] || $PY -m venv .venv
source .venv/bin/activate
if ! python -c "import ultralytics,cv2,flask,torch" 2>/dev/null; then
  python -m pip install --upgrade pip && python -m pip install -r requirements.txt || { echo "INSTALL FAILED - see RUN_ME.md fallback"; exit 1; }
fi
open http://127.0.0.1:5050 http://127.0.0.1:5051 2>/dev/null &
python run.py
