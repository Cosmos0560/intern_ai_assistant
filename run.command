#!/bin/bash
# ============================================================
#  Lumen — one-click start for macOS.
#  Double-click this file in Finder, or run it in a terminal.
#  It sets everything up the first time, then opens the app.
# ============================================================
cd "$(dirname "$0")" || exit 1

echo "──────────────────────────────────────────────"
echo "  Starting Lumen…"
echo "──────────────────────────────────────────────"

# 1) Make sure Python 3 exists.
if ! command -v python3 >/dev/null 2>&1; then
  echo "  ✗ Python 3 is not installed."
  echo "    Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "  Press Enter to close…" _
  exit 1
fi

# 2) Create the virtual environment the first time.
if [ ! -x ".venv/bin/python" ]; then
  echo "  • First run: creating environment (takes a minute)…"
  python3 -m venv .venv || { echo "  ✗ Could not create environment."; read -r -p "  Enter…" _; exit 1; }
fi

# 3) Install / update the libraries (quiet, safe to repeat).
echo "  • Checking libraries…"
./.venv/bin/pip install --quiet --upgrade pip >/dev/null 2>&1
./.venv/bin/pip install --quiet -r requirements.txt || { echo "  ✗ Install failed."; read -r -p "  Enter…" _; exit 1; }

# 4) Open the browser shortly after the server starts.
( sleep 3; open "http://127.0.0.1:5000" ) &

echo "──────────────────────────────────────────────"
echo "  Lumen is ready →  http://127.0.0.1:5000"
echo "  (Keep this window open. Close it to stop the app.)"
echo "──────────────────────────────────────────────"

# 5) Run the server (this holds the window open).
./.venv/bin/python app.py
