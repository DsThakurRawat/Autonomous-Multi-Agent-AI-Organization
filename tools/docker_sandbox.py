"""
Docker Sandbox Tool - Extreme Isolation for Agent Code Execution.
Enforces military-grade sandboxing by wrapping agent code in ephemeral containers.
No internet access by default unless explicitly allowed.
"""

import os
import uuid

import structlog

from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class DockerSandboxTool(BaseTool):
    NAME = "docker_sandbox"
    DESCRIPTION = "Runs arbitrary shell commands or code securely inside an isolated, internet-disabled Docker environment."
    TIMEOUT_S = 300  # 5 minutes for compilation

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.local_mode = os.getenv("AI_ORG_LOCAL_MODE", "false").lower() == "true"
        self.host_workspace = os.getenv("AI_ORG_LOCAL_WORKSPACE", os.getcwd())

    async def run(
        self,
        action: str,
        cmd: str,
        image: str = "python:3.11-slim",
        allow_internet: bool = False,
        **kwargs,
    ) -> ToolResult:
        if action == "execute":
            return await self._execute_sandboxed(cmd, image, allow_internet, **kwargs)
        else:
            return ToolResult(False, "", error=f"Unknown sandbox action {action}")

    async def _execute_sandboxed(
        self, cmd: str, image: str, allow_internet: bool, env: dict[str, str] | None = None, **kwargs
    ) -> ToolResult:
        """
        Spins up an ephemeral container mapped to the project workspace.
        """
        container_name: str = f"ai-org-sandbox-{uuid.uuid4().hex[:8]}"
        c_name: str = container_name
        logger.info("Spawning execution sandbox", container=c_name[:12], image=image)

        # Build the docker run command to ensure isolation
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "-v",
            f"{os.path.abspath(self.host_workspace if self.local_mode else self.working_dir)}:/workspace",
            "-w",
            "/workspace",
        ]

        # Add environment variables
        if env:
            for k, v in env.items():
                docker_cmd.extend(["-e", f"{k}={v}"])

        # Enforce strict network isolation representing Moltbot security constraints
        if not allow_internet:
            docker_cmd.extend(["--network", "none"])

        # Prevent container privilege escalation (military-grade sandbox)
        docker_cmd.extend(["--cap-drop=ALL", "--security-opt=no-new-privileges"])

        # Optional memory constraints matching our Finance/Pruning logic
        docker_cmd.extend(["--memory", "512m", "--cpus", "1.0"])

        # Combine with the actual command
        # E.g. ["docker", "run", "...", "python:3.11-slim", "sh", "-c", "pytest"]
        docker_cmd.extend([image, "sh", "-c", cmd])

        # We fall back to the native `_run_subprocess` provided by BaseTool which enforces timeouts
        logger.debug("Executing isolated tool command", raw_cmd=" ".join(docker_cmd))
        result = await self._run_subprocess(docker_cmd)

        if result.success:
            logger.info("Sandbox execution succeeded", container=c_name[:12])
        else:
            logger.warning(
                "Sandbox execution failed",
                container=c_name[:12],
                error=result.error,
            )

        return result
