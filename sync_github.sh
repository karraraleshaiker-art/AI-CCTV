#!/usr/bin/env bash
set -euo pipefail

BRANCH="${1:-main}"
COMMIT_MESSAGE="${2:-Auto update $(date '+%Y-%m-%d %H:%M:%S')}"

echo "Syncing with origin/${BRANCH}..."
git fetch origin
git pull --rebase --autostash origin "$BRANCH"

echo "Checking for local changes..."
git add -A

if git diff --cached --quiet; then
  echo "No local changes to commit."
else
  git commit -m "$COMMIT_MESSAGE"
fi

echo "Pushing to origin/${BRANCH}..."
git push origin "$BRANCH"

echo "Done."
