# Pull Request Orchestration Guide

To manage 60+ changes across 50+ Pull Requests, we will use a **Branch-per-Feature** strategy. This allows you to review and merge small, atomic changes.

## Logical Groupings (The PR Batches)

I recommend grouping the 60 files into these 10 logical batches to avoid massive commit noise, but I have provided a script below if you wish to do them individually.

1.  **Security Core**: `internal/shared/crypto`, `Dockerfile.proxy`, `secret_manager.go`.
2.  **Infrastructure**: `health/orchestrator.go`, `workers/`, `docker-compose.yml`.
3.  **Base Agents**: `agents/base_agent.py`, `agents/agent_service.py`.
4.  **Specialized Agents**: 1 PR each for `ceo_agent.py`, `cto_agent.py`, etc.
5.  **Go Orchestrator**: `go-backend/cmd/orchestrator/main.go`, `grpc.go`.
6.  **Python Orchestrator**: `planner.py`, `task_graph.py`, `cost_ledger.py`.
7.  **Messaging**: `messaging/`, `kafka_dispatcher.py`.
8.  **Tools & Utilities**: `browser_tool.py`, `linter_tool.py`, `logging_config.py`.
9.  **Observability**: `metrics.py`, `tracing.py`, `tui.py`.
10. **Documentation**: `README.md`, `SETUP.md`, `migrations/`.

---

## Automation Script

If you truly want to hit the **50+ PR** mark, you can run this script to create a separate branch and commit for groups of 1-2 files.

```bash
#!/bin/bash
# pr_maker.sh - Automates branch creation and pushing for individual files

# Usage: ./pr_maker.sh <file_path> <branch_name> <commit_message>

FILE=$1
BRANCH=$2
MSG=$3

if [ -z "$FILE" ]; then
    echo "Usage: ./pr_maker.sh <file_path> <branch_name> <commit_message>"
    exit 1
fi

# 1. Create and switch to new branch from main
git checkout main
git pull origin main
git checkout -b "$BRANCH"

# 2. Add only the specific file/directory
git add "$FILE"

# 3. Commit
git commit -m "$MSG"

# 4. Push
git push origin "$BRANCH"

echo "Branch $BRANCH pushed. Visit GitHub to open the PR."
git checkout main
```

## How to raise 50 PRs fast:
1. Pick a file from the `git status` list.
2. Run: `./pr_maker.sh agents/ceo_agent.py feat/ceo-hardening "Hardening CEO agent logic"`
3. Click the link GitHub gives you in the terminal to CREATE the PR.
4. Repeat for all files.
