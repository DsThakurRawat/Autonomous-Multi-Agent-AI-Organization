#!/bin/bash
# pr_maker.sh - Automates branch creation and pushing for individual files

FILE=$1
BRANCH=$2
MSG=$3

if [ -z "$FILE" ] || [ -z "$BRANCH" ] || [ -z "$MSG" ]; then
    echo "Usage: ./pr_maker.sh <file_path> <branch_name> <commit_message>"
    echo "Example: ./pr_maker.sh agents/ceo_agent.py feat/ceo-hardening 'Hardening CEO agent'"
    exit 1
fi

# 1. Sync with main
git checkout main
git pull origin main

# 2. Create branch
git checkout -b "$BRANCH"

# 3. Add and commit
git add "$FILE"
git commit -m "$MSG"

# 4. Push
git push origin "$BRANCH"

echo "----------------------------------------------------"
echo "✅ Branch $BRANCH pushed!"
echo "Next step: Go to GitHub to open the Pull Request."
echo "----------------------------------------------------"

# 5. Return to main for next PR
git checkout main
