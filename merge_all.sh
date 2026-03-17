#!/bin/bash
# merge_all.sh - Merges all feature branches into main

git checkout main
git pull origin main

# Get all branches starting with feat/ or chore/
BRANCHES=$(git branch --list 'feat/*' 'chore/*' | sed 's/*//g' | xargs)

for BRANCH in $BRANCHES; do
    echo "Merging $BRANCH..."
    git merge "$BRANCH" --no-edit || git merge --abort
done

echo "Pushing all merges to origin main..."
git push origin main

echo "✅ All branches merged and pushed to main."
