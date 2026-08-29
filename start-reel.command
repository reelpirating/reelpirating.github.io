#!/bin/zsh

cd "$(dirname "$0")"

echo "Starting Reel Live TV..."

PYTHON3="/usr/bin/python3"

if [ ! -x "$PYTHON3" ]; then
    PYTHON3="$(command -v python3)"
fi

if [ -z "$PYTHON3" ] || [ ! -x "$PYTHON3" ]; then
    echo "ERROR: Python 3 was not found."
    read
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON3" -m venv .venv
fi

VENV_PYTHON="$PWD/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment could not be created."
    read
    exit 1
fi

echo "Installing requirements..."
"$VENV_PYTHON" -m pip install -r requirements-live-tv.txt

echo ""
echo "========================================"
echo "       REEL LIVE TV API"
echo "========================================"
echo ""
echo "Running at:"
echo "http://127.0.0.1:8787"
echo ""
echo "Keep this Terminal window open."
echo ""

"$VENV_PYTHON" live_tv_api.py

echo ""
echo "========================================"
echo "Live TV API stopped."
echo "========================================"
read
