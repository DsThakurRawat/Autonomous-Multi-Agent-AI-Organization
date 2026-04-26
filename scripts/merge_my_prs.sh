#!/bin/bash
# Script to merge specific PRs raised by the user
# PRs: #74, #73, #69

echo "Starting merge process for PRs #74, #73, #69..."

for pr in 74 73 69; do
    echo "Merging PR #$pr..."
    gh pr merge $pr --merge --auto || echo "Failed to merge PR #$pr"
done

echo "Done."
