"""
Agent Collaboration Tool — Enables agents to communicate securely with each other
by leaving persistent messages, code snippets, or architectural notes in a shared space.
"""

import os
import json
import time
from typing import Optional
import structlog
from filelock import FileLock, Timeout

from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)


class CollaborationTool(BaseTool):
    NAME = "collaboration_tool"
    DESCRIPTION = (
        "Enables agent-to-agent communication by posting and reading messages "
        "on a shared collaboration board. Actions: 'post_message', 'read_all', 'clear_board'."
    )
    TIMEOUT_S = 60

    BOARD_FILE = ".agent_collaboration_board.json"
    LOCK_FILE = ".agent_collaboration_board.json.lock"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not os.path.exists(self.BOARD_FILE):
            with FileLock(self.LOCK_FILE, timeout=5):
                with open(self.BOARD_FILE, "w") as f:
                    json.dump([], f)

    async def run(
        self,
        action: str,
        agent_name: str,
        target_agent: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Main entrypoint.
        `action`: 'post_message' | 'read_all' | 'clear_board'
        `agent_name`: Your agent name (e.g. 'CTO', 'Engineer_Backend')
        `target_agent`: (Optional) The specific agent you are addressing
        `message`: The content to post
        """
        actions = {
            "post_message": self._post_message,
            "read_all": self._read_all,
            "clear_board": self._clear_board,
        }

        fn = actions.get(action)
        if not fn:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown collaboration action: {action}",
            )

        logger.info("Executing collaboration action", action=action, agent=agent_name)
        return await fn(
            agent_name=agent_name, target_agent=target_agent, message=message, **kwargs
        )

    async def _post_message(
        self, agent_name: str, target_agent: Optional[str], message: str, **kwargs
    ) -> ToolResult:
        if not message:
            return ToolResult(
                success=False, output="", error="Must provide a 'message' to post."
            )

        try:
            with open(self.BOARD_FILE, "r") as f:
                board = json.load(f)
        except Exception:
            board = []

        entry = {
            "timestamp": time.time(),
            "from_agent": agent_name,
            "to_agent": target_agent or "ALL",
            "message": message,
        }
        board.append(entry)

        with open(self.BOARD_FILE, "w") as f:
            json.dump(board, f, indent=2)

        return ToolResult(
            success=True,
            output=f"Message posted successfully to {target_agent or 'ALL'}.",
            metadata={"board_size": len(board)},
        )

    async def _read_all(self, agent_name: str, **kwargs) -> ToolResult:
        try:
            with open(self.BOARD_FILE, "r") as f:
                board = json.load(f)
        except Exception:
            board = []

            with FileLock(self.LOCK_FILE, timeout=10):
                try:
                    with open(self.BOARD_FILE, "r") as f:
                        board = json.load(f)
                except Exception:
                    board = []
                    
                entry = {
                    "timestamp": time.time(),
                    "from_agent": agent_name,
                    "to_agent": target_agent or "ALL",
                    "message": message
                }
                board.append(entry)
                
                with open(self.BOARD_FILE, "w") as f:
                    json.dump(board, f, indent=2)
                    
            return ToolResult(
                success=True,
                output=f"Message posted successfully to {target_agent or 'ALL'}.",
                metadata={"board_size": len(board)}
            )
        except Timeout:
            logger.error("Timeout acquiring collaboration board lock", agent=agent_name)
            return ToolResult(success=False, output="", error="Timeout acquiring board lock")

    async def _read_all(self, agent_name: str, **kwargs) -> ToolResult:
        try:
            with FileLock(self.LOCK_FILE, timeout=5):
                try:
                    with open(self.BOARD_FILE, "r") as f:
                        board = json.load(f)
                except Exception:
                    board = []
        except Timeout:
            logger.error("Timeout acquiring collaboration board lock for reading", agent=agent_name)
            return ToolResult(success=False, output="", error="Timeout acquiring board lock")
            
        if not board:
            return ToolResult(
                success=True, output="The collaboration board is currently empty."
            )

        formatted_messages = []
        for msg in board:
            # Format: [10:30:15] Backend -> CTO: "I have finished the DB schema."
            t = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
            formatted_messages.append(
                f"[{t}] {msg['from_agent']} -> {msg['to_agent']}:\n{msg['message']}\n"
            )

        return ToolResult(success=True, output="\n".join(formatted_messages))

    async def _clear_board(self, agent_name: str, **kwargs) -> ToolResult:
        with open(self.BOARD_FILE, "w") as f:
            json.dump([], f)
        return ToolResult(success=True, output="Collaboration board has been cleared.")
        try:
            with FileLock(self.LOCK_FILE, timeout=5):
                with open(self.BOARD_FILE, "w") as f:
                    json.dump([], f)
            return ToolResult(
                success=True,
                output="Collaboration board has been cleared."
            )
        except Timeout:
            logger.error("Timeout acquiring collaboration board lock for clearing", agent=agent_name)
            return ToolResult(success=False, output="", error="Timeout acquiring board lock")
