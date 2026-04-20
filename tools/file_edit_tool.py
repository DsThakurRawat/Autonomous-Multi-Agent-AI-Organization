"""
Local File Edit Tool - High-precision string replacement with fuzzy fallback.

Matching Strategy (3-tier):
  1. Exact match — current behavior, 100% confidence.
  2. Normalized whitespace — collapse runs of spaces/tabs, ~95% confidence.
  3. Line-level difflib — SequenceMatcher best-window scan, configurable threshold.

Every successful edit produces a unified diff in ToolResult.metadata["diff"].
"""

import difflib
import os
import re

import structlog

from .base_tool import BaseTool, ToolResult

logger = structlog.get_logger(__name__)

# Minimum similarity ratio for difflib fallback matches
_DIFFLIB_THRESHOLD = 0.85


class LocalFileEditTool(BaseTool):
    NAME = "file_edit"
    DESCRIPTION = (
        "Performs string replacements in local files. Uses exact matching by "
        "default with automatic fuzzy fallback when whitespace differs."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def run(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> ToolResult:
        """
        Args:
            file_path: Path to the file relative to working_dir.
            old_string: The string to find (exact or fuzzy-matched).
            new_string: The replacement string.
            replace_all: If True, replace all occurrences. If False, fail on
                         multiple matches (for safety).
        """
        full_path = os.path.join(self.working_dir, file_path)

        if not os.path.exists(full_path):
            return ToolResult(
                success=False, output="", error=f"File not found: {file_path}"
            )

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # ------- Tier 1: Exact match -------
            exact_count = content.count(old_string)

            if exact_count == 1 or (exact_count > 1 and replace_all):
                new_content = content.replace(
                    old_string, new_string, -1 if replace_all else 1
                )
                return self._write_and_respond(
                    full_path,
                    file_path,
                    content,
                    new_content,
                    match_count=exact_count if replace_all else 1,
                    strategy="exact",
                    confidence=1.0,
                )

            if exact_count > 1 and not replace_all:
                return ToolResult(
                    success=False,
                    output="",
                    error=(
                        f"Found {exact_count} exact matches for the target string. "
                        "Use 'replace_all=True' or provide more surrounding context "
                        "to uniquely identify the block."
                    ),
                )

            # exact_count == 0 → fall through to fuzzy tiers

            # ------- Tier 2: Normalized whitespace -------
            match = self._normalized_find(content, old_string)
            if match is not None:
                start, end = match
                new_content = content[:start] + new_string + content[end:]
                return self._write_and_respond(
                    full_path,
                    file_path,
                    content,
                    new_content,
                    match_count=1,
                    strategy="normalized_whitespace",
                    confidence=0.95,
                )

            # ------- Tier 3: Line-level difflib -------
            match = self._difflib_find(content, old_string)
            if match is not None:
                start, end, ratio = match
                new_content = content[:start] + new_string + content[end:]
                return self._write_and_respond(
                    full_path,
                    file_path,
                    content,
                    new_content,
                    match_count=1,
                    strategy="difflib",
                    confidence=round(ratio, 4),
                )

            # ------- All tiers failed -------
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"String to replace not found in {file_path} "
                    "(tried exact, normalized-whitespace, and fuzzy matching). "
                    "Ensure the target text exists in the file."
                ),
            )

        except Exception as e:
            logger.error("File edit failed", file=file_path, error=str(e))
            return ToolResult(
                success=False, output="", error=f"Failed to edit file: {str(e)}"
            )

    # ── Matching helpers ─────────────────────────────────────────────

    @staticmethod
    def _normalized_find(content: str, target: str) -> tuple[int, int] | None:
        """Find *target* in *content* after collapsing whitespace runs.

        Preserves newlines — only horizontal whitespace (spaces/tabs) is
        collapsed so that multi-line blocks still align correctly.

        Returns ``(start, end)`` indices into the **original** *content*,
        or ``None`` if no match.
        """
        _ws = re.compile(r"[ \t]+")
        norm_content = _ws.sub(" ", content)
        norm_target = _ws.sub(" ", target)

        idx = norm_content.find(norm_target)
        if idx == -1:
            return None

        # Map normalized index back to original content position
        orig_start = _map_norm_to_orig(content, norm_content, idx)
        orig_end = _map_norm_to_orig(
            content, norm_content, idx + len(norm_target)
        )
        return (orig_start, orig_end)

    @staticmethod
    def _difflib_find(
        content: str,
        target: str,
        threshold: float = _DIFFLIB_THRESHOLD,
    ) -> tuple[int, int, float] | None:
        """Slide a window of *target* lines over *content* lines and return
        the best fuzzy match above *threshold*.

        Returns ``(start_char, end_char, ratio)`` or ``None``.
        """
        content_lines = content.splitlines(keepends=True)
        target_lines = target.splitlines(keepends=True)

        if not target_lines:
            return None

        window = len(target_lines)
        best_ratio = 0.0
        best_range: tuple[int, int] | None = None

        for i in range(len(content_lines) - window + 1):
            candidate = content_lines[i : i + window]
            ratio = difflib.SequenceMatcher(
                None, candidate, target_lines
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_range = (i, i + window)

        if best_ratio >= threshold and best_range is not None:
            start_char = sum(len(l) for l in content_lines[: best_range[0]])
            end_char = sum(len(l) for l in content_lines[: best_range[1]])
            return (start_char, end_char, best_ratio)

        return None

    # ── Write & respond ──────────────────────────────────────────────

    def _write_and_respond(
        self,
        full_path: str,
        file_path: str,
        old_content: str,
        new_content: str,
        *,
        match_count: int,
        strategy: str,
        confidence: float,
    ) -> ToolResult:
        """Atomically write *new_content* and return a ToolResult with diff."""
        # Atomic write: tmp → rename
        tmp_path = full_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, full_path)

        # Generate unified diff for TUI/logging
        diff_lines = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=3,
        )
        diff_text = "".join(diff_lines)

        logger.info(
            "File edited successfully",
            file=file_path,
            matches=match_count,
            strategy=strategy,
            confidence=confidence,
        )

        return ToolResult(
            success=True,
            output=(
                f"Successfully updated {file_path}. "
                f"{match_count} occurrence(s) replaced "
                f"(strategy={strategy}, confidence={confidence})."
            ),
            error=None,
            metadata={
                "diff": diff_text,
                "match_strategy": strategy,
                "match_confidence": confidence,
            },
        )


# ── Module-level utility ─────────────────────────────────────────────


def _map_norm_to_orig(
    original: str, normalized: str, norm_idx: int
) -> int:
    """Map a character index in the *normalized* string back to the
    corresponding index in the *original* string.

    Both strings must have been produced by collapsing ``[ \\t]+`` → ``" "``.
    """
    orig_i = 0
    norm_i = 0
    while norm_i < norm_idx and orig_i < len(original):
        if original[orig_i] in (" ", "\t"):
            # Walk past the full whitespace run in original
            while orig_i < len(original) and original[orig_i] in (" ", "\t"):
                orig_i += 1
            # The normalized string consumed exactly one space
            norm_i += 1
        else:
            orig_i += 1
            norm_i += 1
    return orig_i
