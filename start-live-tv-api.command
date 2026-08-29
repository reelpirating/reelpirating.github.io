#!/bin/zsh
set -e
cd "$(dirname "$0")"
PYTHON="$(command -v python3)"
if [ -z "$PYTHON" ]; then echo "Python 3 is required."; read; exit 1; fi
if [ ! -d .reel-live-venv ]; then
  "$PYTHON" -m venv .reel-live-venv
fi
source .reel-live-venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements-live-tv.txt
python -m playwright install chromium
python live_tv_api.py
