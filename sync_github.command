#!/usr/bin/env bash
# AI-CCTV Synchronization & Launch Script (for Ali / macOS Double-Clickable)
set -euo pipefail

cd "$(dirname "$0")"

BRANCH="${1:-main}"

echo "======================================================"
echo "   AI-CCTV — Factory Monitoring System Sync (Ali)"
echo "   Al Noor Factory for Solar Panels"
echo "======================================================"
echo ""

# Step 1: Internet Connectivity Check
echo "[1/4] Checking internet connectivity..."
if ! curl -s --head --connect-timeout 4 https://github.com >/dev/null 2>&1 && \
   ! curl -s --head --connect-timeout 4 https://www.google.com >/dev/null 2>&1; then
    echo ""
    echo "======================================================================"
    echo " ⚠️  WARNING:"
    echo " You must be connected to the internet to prevent code conflicts"
    echo " with your partner Karrar."
    echo "======================================================================"
    echo ""
    read -p "Press Enter to exit..." || true
    exit 1
fi
echo "✓ Internet connection verified."
echo ""

# Step 2: GitHub Synchronization
echo "[2/4] Syncing with origin/${BRANCH}..."
git fetch origin
git pull --rebase --autostash origin "$BRANCH"
echo "✓ Repository is up to date."
echo ""

# Detect Python binary
PYTHON_CMD="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

# Step 3: Launch Logs Reader (port 8808) in its own independent browser window
echo "[3/4] Starting Logs Reader on http://127.0.0.1:8808 ..."
$PYTHON_CMD logs_reader.py >/dev/null 2>&1 &
LOGS_PID=$!
echo "✓ Logs Reader started (PID: $LOGS_PID)."
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
echo "AI CCTV stopped. Session finished."
read -p "Press Enter to close..." || true
