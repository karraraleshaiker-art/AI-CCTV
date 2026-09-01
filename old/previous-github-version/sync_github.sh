#!/usr/bin/env bash
# AI-CCTV Synchronization & Launch Script (for Karrar / Linux & Git Bash)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

BRANCH="${1:-main}"

if [ ! -d ".git" ]; then
    echo "ERROR: This script must be run from inside the AI-CCTV Git repository."
    echo "Current folder: $PWD"
    exit 1
fi

echo "======================================================"
echo "   AI-CCTV — Factory Monitoring System Sync (Karrar)"
echo "   Al Noor Factory for Solar Panels"
echo "======================================================"
echo ""

# Step 1: Internet Connectivity Check
echo "[1/4] Checking internet connectivity..."
if ! curl -s --head --connect-timeout 4 https://github.com >/dev/null 2>&1 && \
   ! curl -s --head --connect-timeout 4 https://www.google.com >/dev/null 2>&1; then
    echo ""
    echo "======================================================================"
    echo " [WARNING]"
    echo " You must be connected to the internet to prevent code conflicts"
    echo " with your partner Ali."
    echo "======================================================================"
    echo ""
    exit 1
fi
echo "[OK] Internet connection verified."
echo ""

# Step 2: GitHub Synchronization
echo "[2/4] Syncing with origin/${BRANCH}..."
git fetch origin
git pull --rebase --autostash origin "$BRANCH"
echo "[OK] Repository is up to date."
echo ""

# Detect Python binary. Prefer the project venv so Windows does not accidentally
# launch an unsupported system Python.
PYTHON_CMD=""
IS_WINDOWS_BASH=0
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*) IS_WINDOWS_BASH=1 ;;
esac

detect_python() {
    if [ -f ".venv/bin/python" ]; then
        PYTHON_CMD="./.venv/bin/python"
    elif [ -f ".venv/Scripts/python.exe" ]; then
        PYTHON_CMD="./.venv/Scripts/python.exe"
    elif [ -f "venv/bin/python" ]; then
        PYTHON_CMD="./venv/bin/python"
    elif [ -f "venv/Scripts/python.exe" ]; then
        PYTHON_CMD="./venv/Scripts/python.exe"
    elif [ "$IS_WINDOWS_BASH" -eq 0 ] && command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif [ "$IS_WINDOWS_BASH" -eq 0 ] && command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    fi
}

detect_python

if [ -z "$PYTHON_CMD" ] && [ "$IS_WINDOWS_BASH" -eq 1 ]; then
    echo "[SETUP] .venv was not found. Starting setup_venv.bat..."
    echo "Choose option 2 for the Full Web Platform when prompted."
    echo ""

    if ! cmd.exe /c setup_venv.bat; then
        echo "ERROR: setup_venv.bat did not complete successfully."
        exit 1
    fi

    PYTHON_CMD=""
    detect_python
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python was not found."
    echo "Run setup_venv.bat on Windows, or create a venv and install requirements-web.txt."
    exit 1
fi

# Step 3: Launch Logs Reader (port 8808) in its own independent browser window
echo "[3/4] Starting Logs Reader on http://127.0.0.1:8808 ..."
$PYTHON_CMD logs_reader.py >/dev/null 2>&1 &
LOGS_PID=$!
echo "[OK] Logs Reader started (PID: $LOGS_PID)."
echo ""

# Trap cleanup to terminate background logs_reader when main app closes
cleanup() {
    echo ""
    echo "Shutting down background services..."
    kill "$LOGS_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Step 4: Launch Main AI CCTV Platform (port 8000) in its own browser window
echo "[4/4] Starting AI CCTV Web Platform on http://127.0.0.1:8000 ..."
echo "======================================================"
$PYTHON_CMD app.py

echo ""
echo "AI CCTV stopped. Closing session."
