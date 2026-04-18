"""
Local File Edit Tool - High-precision string replacement tool inspired by Claw/Clawd.
Avoids full-file rewrites and ensures indentation preservation.
"""

import os
import re
import structlog
from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)

class LocalFileEditTool(BaseTool):
    NAME = "file_edit"
    DESCRIPTION = "Performs exact string replacements in local files. Requires 'old_string' to match exactly (including indentation) and be unique."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def run(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        """
        Args:
            file_path: Path to the file relative to working_dir
            old_string: The exact string to find (must be unique)
            new_string: The string to replace it with
            replace_all: If True, replace all occurrences. If False, fail if multiple matches exist.
        """
        full_path = os.path.join(self.working_dir, file_path)
        
        if not os.path.exists(full_path):
            return ToolResult(success=False, output="", error=f"File not found: {file_path}")

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count occurrences
            matches = content.count(old_string)
            
            if matches == 0:
                # Log a snippet of the file to help the agent debug
                snippet = content[:500] + "..." if len(content) > 500 else content
                return ToolResult(
                    success=False, 
                    output="", 
                    error=f"String to replace not found in {file_path}. Ensure exact match including whitespace/indentation."
                )
            
            if matches > 1 and not replace_all:
                return ToolResult(
                    success=False, 
                    output="", 
                    error=f"Found {matches} matches for the target string. Use 'replace_all=True' or provide more surrounding context to uniquely identify the block."
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            # Write back atomically
            tmp_path = full_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            os.replace(tmp_path, full_path)
            
            logger.info("File edited successfully", file=file_path, matches=matches, replace_all=replace_all)
            return ToolResult(
                success=True, 
                output=f"Successfully updated {file_path}. {matches} occurrence(s) replaced.", 
                error=None
            )

        except Exception as e:
            logger.error("File edit failed", file=file_path, error=str(e))
            return ToolResult(success=False, output="", error=f"Failed to edit file: {str(e)}")
