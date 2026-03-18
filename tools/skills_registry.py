"""
Skills Registry Tool - The "ClawHub Integration" for loading external capabilities on-the-fly.
Allows the AI to dynamically discover and download new execution skills to its sandbox.
"""

import importlib
import os
import sys
from typing import Any

import structlog

from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class SkillsRegistryTool(BaseTool):
    NAME = "skills_registry"
    DESCRIPTION = (
        "Dynamically downloads and installs external agent tools/skills at runtime."
    )
    TIMEOUT_S = 180

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.installed_skills: dict[str, Any] = {}
        self.skills_dir = os.path.join(self.working_dir, ".skills")
        os.makedirs(self.skills_dir, exist_ok=True)
        # Ensure our temporary skills are importable
        if self.skills_dir not in sys.path:
            sys.path.append(self.skills_dir)

    async def run(self, action: str, skill_name: str, **kwargs) -> ToolResult:
        if action == "install":
            return await self._install_skill(skill_name)
        elif action == "execute":
            return await self._execute_skill(skill_name, **kwargs)
        else:
            return ToolResult(False, "", error=f"Unknown registry action {action}")

    async def _install_skill(self, skill_name: str) -> ToolResult:
        """
        Mock for fetching a Python script from a remote registry (e.g. ClawHub)
        and installing its pip dependencies.
        """
        logger.info("Installing new skill from registry", skill=skill_name)

        # Simulating a dynamic download of a Python snippet
        skill_path = os.path.join(self.skills_dir, f"{skill_name}.py")

        if not os.path.exists(skill_path):
            # In a real system, `requests.get("https://clawhub.dev/skills/{skill_name}.py")`
            mock_code = f"""
def execute(**kwargs):
    return f"Executed dynamically loaded skill '{skill_name}' with args: {{kwargs}}"
"""
            with open(skill_path, "w") as f:
                f.write(mock_code)

        return ToolResult(
            success=True,
            output=f"Successfully downloaded and mounted {skill_name} into agent sandbox.",
        )

    async def _execute_skill(self, skill_name: str, **kwargs) -> ToolResult:
        """Dynamically imports and executes a mounted skill."""
        logger.info("Executing dynamic skill", skill=skill_name)
        if skill_name in sys.modules:
            module = importlib.reload(sys.modules[skill_name])
        else:
            try:
                module = importlib.import_module(skill_name)
            except ImportError as e:
                return ToolResult(
                    False, "", error=f"Skill {skill_name} not installed. {e}"
                )

        try:
            # Assuming the skill exports an `execute` function
            result = module.execute(**kwargs)
            return ToolResult(True, output=str(result))
        except Exception as e:
            return ToolResult(
                False, "", error=f"Execution of scalar skill {skill_name} failed: {e}"
            )
