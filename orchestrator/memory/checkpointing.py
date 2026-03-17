from datetime import UTC, datetime
import json
import os
from typing import Any

import structlog

from tools.git_tool import GitTool

logger = structlog.get_logger(__name__)


class CheckpointManager:
    """
    Manages state checkpoints using a shadow Git branch (inspired by `cli`/Entire).!
    Allows instant rewinding of the project workspace state and AI memory if an agent hallucinates.
    """

    CHECKPOINT_BRANCH = "ai-org/checkpoints/v1"

    def __init__(self, project_id: str, output_dir: str):
        self.project_id = project_id
        self.workspace_dir = os.path.join(output_dir, project_id)
        self.git = GitTool(repo_path=self.workspace_dir)
        self._initialized = False

    async def _ensure_git_repo(self):
        if self._initialized:
            return
        os.makedirs(self.workspace_dir, exist_ok=True)

        # Initialize standard Git repo
        if not os.path.exists(os.path.join(self.workspace_dir, ".git")):
            await self.git.run("init")

        self._initialized = True

    async def save_checkpoint(
        self, task_name: str, agent_role: str, memory_state: dict[str, Any]
    ) -> None:
        """
        Hooks into the Orchestrator.
        Captures the exact workspace state AND internal memory attributes into the shadow branch.
        """
        await self._ensure_git_repo()

        # Serialize AI memory state into workspace so it gets versioned
        state_dir = os.path.join(self.workspace_dir, ".ai-org")
        os.makedirs(state_dir, exist_ok=True)
        state_file = os.path.join(state_dir, "memory_state.json")

        # Safe persistence of dataclasses/models
        # Since memory_state might contain raw text or dicts, ensure json safety
        with open(state_file, "w") as f:
            json.dump(memory_state, f, indent=2, default=str)

        # Ensure we are operating perfectly on the shadow branch
        status_check = await self.git._run_subprocess(
            ["git", "branch", "--show-current"], cwd=self.workspace_dir
        )

        current_branch = status_check.output.strip()
        if not current_branch:
            # Empty repo, we need an initial commit before we can branch
            await self.git.run("add", files=".")
            await self.git.run("commit", message="Initial project bootstrap")
            await self.git._run_subprocess(
                ["git", "checkout", "-b", self.CHECKPOINT_BRANCH],
                cwd=self.workspace_dir,
            )
        elif current_branch != self.CHECKPOINT_BRANCH:
            # Check if shadow branch exists, if not create it
            b_check = await self.git._run_subprocess(
                ["git", "show-ref", "--verify", f"refs/heads/{self.CHECKPOINT_BRANCH}"],
                cwd=self.workspace_dir,
            )
            if b_check.success:
                await self.git._run_subprocess(
                    ["git", "checkout", self.CHECKPOINT_BRANCH], cwd=self.workspace_dir
                )
            else:
                await self.git._run_subprocess(
                    ["git", "checkout", "-b", self.CHECKPOINT_BRANCH],
                    cwd=self.workspace_dir,
                )

        # Stage snapshots
        await self.git.run("add", files=".")

        # ── Atomic Sync Barrier ──────────────────────────────────────────
        # Ensure all OS file buffers are flushed to disk before committing
        if hasattr(os, "sync"):
            os.sync()

        # Verify state file integrity before committing
        if not os.path.exists(state_file):
             logger.warning("Memory state file missing during checkpoint, skipping barrier verification")

        diff_res = await self.git.run("diff", staged=True)
        if not diff_res.output.strip():
            logger.debug(
                "No operational changes detected for checkpoint.", task_name=task_name
            )
            return

        # metadata for better observability
        msg = (
            f"Checkpoint: {task_name}\n"
            f"Agent: {agent_role}\n"
            f"Timestamp: {datetime.now(UTC).isoformat()}\n"
            f"Project: {self.project_id}\n"
            f"Status: snapshot_verified"
        )
        res = await self.git.run("commit", message=msg)

        if res.success:
            logger.info(
                "Shadow checkpoint committed successfully.",
                task_name=task_name,
                agent=agent_role,
            )
        else:
            logger.warning("Shadow checkpoint failed.", error=res.error)

    async def list_checkpoints(self) -> list[dict[str, str]]:
        """Returns the timeline of agent execution checkpoints."""
        await self._ensure_git_repo()
        res = await self.git.run("log", n=50)
        checkpoints = []
        if res.success:
            for line in res.output.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        checkpoints.append({"hash": parts[0], "message": parts[1]})
        return checkpoints

    async def rewind(self, commit_hash: str, force: bool = False) -> dict[str, Any] | None:
        """
        Hard undo to a precise checkpoint hash.
        Cleans the workspace and returns the restored ProjectMemory state for the Orchestrator.
        Requires force=True to execute.
        """
        if not force:
            logger.error("Rewind aborted. 'force=True' is required for destructive checkpoint rewinds.")
            return None

        await self._ensure_git_repo()

        # 1. Hard reset to checkpoint
        res = await self.git._run_subprocess(
            ["git", "reset", "--hard", commit_hash], cwd=self.workspace_dir
        )
        if not res.success:
            logger.error(
                "Failed to rewind workspace", hash=commit_hash, error=res.error
            )
            return None

        # 2. Obliterate any untracked garbage files generated by hallucinations
        await self.git._run_subprocess(["git", "clean", "-fd"], cwd=self.workspace_dir)

        logger.info("Workspace successfully rewound.", hash=commit_hash)

        # 3. Reload the orchestrator's state memory
        state_file = os.path.join(self.workspace_dir, ".ai-org", "memory_state.json")
        if os.path.exists(state_file):
            with open(state_file) as f:
                return json.load(f)

        return None
