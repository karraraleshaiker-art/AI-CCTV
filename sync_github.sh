#!/usr/bin/env bash
# AI-CCTV Synchronization & Launch Script (for Karrar / Linux & Git Bash)
set -euo pipefail

cd "$(dirname "$0")"

BRANCH="${1:-main}"

echo "======================================================"
echo "   AI-CCTV — Factory Monitoring System Sync (Karrar)"
echo "   Al Noor Factory for Solar Panels"
echo "======================================================"
echo ""

# Step 1: Internet Connectivity Check
echo "[1/3] Checking internet connectivity..."
if ! curl -s --head --connect-timeout 4 https://github.com >/dev/null 2>&1 && \
   ! curl -s --head --connect-timeout 4 https://www.google.com >/dev/null 2>&1; then
    echo ""
    echo "======================================================================"
    echo " ⚠️  WARNING:"
    echo " You must be connected to the internet to prevent code conflicts"
    echo " with your partner Ali."
    echo "======================================================================"
    echo ""
    exit 1
fi
echo "✓ Internet connection verified."
echo ""

# Step 2: GitHub Synchronization
echo "[2/3] Syncing with origin/${BRANCH}..."
git fetch origin
git pull --rebase --autostash origin "$BRANCH"
echo "✓ Repository is up to date."
echo ""

# Step 3: Launch FastAPI Web Dashboard & AI Core Application
echo "[3/3] Starting AI CCTV Web Platform (FastAPI)..."
echo "======================================================"
PYTHON_CMD="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_CMD=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

$PYTHON_CMD app.py

echo ""
echo "AI CCTV stopped. Closing session."
