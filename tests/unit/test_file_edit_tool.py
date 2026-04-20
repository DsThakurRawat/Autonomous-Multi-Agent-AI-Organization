"""
Unit Tests — LocalFileEditTool (3-tier fuzzy matching)

Tests the rewritten file edit tool's exact, normalized whitespace,
and difflib-based matching strategies, plus atomic write safety
and diff output generation.
"""

import os

import pytest

from tools.file_edit_tool import LocalFileEditTool


@pytest.fixture
def tool(tmp_path):
    """Create a LocalFileEditTool rooted in a temporary directory."""
    t = LocalFileEditTool()
    t.working_dir = str(tmp_path)
    return t


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample Python file for editing tests."""
    content = '''def hello():
    print("Hello, world!")

def goodbye():
    print("Goodbye, world!")

class MyClass:
    def __init__(self):
        self.value = 42
'''
    path = tmp_path / "sample.py"
    path.write_text(content)
    return "sample.py"


# ── Tier 1: Exact Match ─────────────────────────────────────────────


class TestExactMatch:
    @pytest.mark.asyncio
    async def test_exact_single_replace(self, tool, sample_file):
        result = await tool.run(
            file_path=sample_file,
            old_string='print("Hello, world!")',
            new_string='print("Hi, world!")',
        )
        assert result.success
        assert "exact" in result.metadata.get("match_strategy", "")
        assert result.metadata["match_confidence"] == 1.0

        # Verify file was actually changed
        full_path = os.path.join(tool.working_dir, sample_file)
        content = open(full_path).read()
        assert 'print("Hi, world!")' in content
        assert 'print("Hello, world!")' not in content

    @pytest.mark.asyncio
    async def test_exact_match_preserves_indentation(self, tool, sample_file):
        result = await tool.run(
            file_path=sample_file,
            old_string="        self.value = 42",
            new_string="        self.value = 99",
        )
        assert result.success
        full_path = os.path.join(tool.working_dir, sample_file)
        content = open(full_path).read()
        assert "        self.value = 99" in content

    @pytest.mark.asyncio
    async def test_multiple_matches_without_flag_fails(self, tool, tmp_path):
        (tmp_path / "dup.txt").write_text("foo\nfoo\nbar")
        result = await tool.run(
            file_path="dup.txt",
            old_string="foo",
            new_string="baz",
        )
        assert not result.success
        assert "2" in result.error  # Should mention count

    @pytest.mark.asyncio
    async def test_multiple_matches_with_replace_all(self, tool, tmp_path):
        (tmp_path / "dup.txt").write_text("foo\nfoo\nbar")
        result = await tool.run(
            file_path="dup.txt",
            old_string="foo",
            new_string="baz",
            replace_all=True,
        )
        assert result.success
        content = (tmp_path / "dup.txt").read_text()
        assert content == "baz\nbaz\nbar"

    @pytest.mark.asyncio
    async def test_file_not_found(self, tool):
        result = await tool.run(
            file_path="nonexistent.py",
            old_string="x",
            new_string="y",
        )
        assert not result.success
        assert "not found" in result.error.lower()


# ── Tier 2: Normalized Whitespace ────────────────────────────────────


class TestNormalizedWhitespace:
    @pytest.mark.asyncio
    async def test_tabs_vs_spaces(self, tool, tmp_path):
        """LLM sends spaces but file has tabs — should still match."""
        (tmp_path / "tabs.py").write_text("def foo():\n\tprint('hello')\n")
        result = await tool.run(
            file_path="tabs.py",
            old_string="def foo():\n print('hello')",  # spaces instead of tab
            new_string="def foo():\n\tprint('goodbye')",
        )
        assert result.success
        assert result.metadata["match_strategy"] == "normalized_whitespace"
        assert result.metadata["match_confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_extra_spaces_in_target(self, tool, tmp_path):
        """LLM adds extra spaces — should still match."""
        (tmp_path / "spaces.py").write_text("x = 1 + 2\n")
        result = await tool.run(
            file_path="spaces.py",
            old_string="x  =  1  +  2",  # extra spaces
            new_string="x = 3 + 4",
        )
        assert result.success
        assert result.metadata["match_strategy"] == "normalized_whitespace"


# ── Tier 3: Difflib Fuzzy Match ──────────────────────────────────────


class TestDifflibFuzzy:
    @pytest.mark.asyncio
    async def test_minor_typo_matches(self, tool, tmp_path):
        """A character-level typo should fall through to difflib fuzzy match.

        _difflib_find compares lists of lines, so we need enough matching
        lines that one changed line keeps the ratio >= 0.85.
        With 8 lines and 1 different: ratio ≈ 7/8 = 0.875.
        """
        original = (
            "import os\n"
            "import sys\n"
            "\n"
            "def process_data():\n"
            "    data = load_file()\n"
            "    result = transform(data)\n"
            "    logger.info(result)\n"
            "    return result\n"
        )
        (tmp_path / "fuzzy.py").write_text(original)

        # LLM search string has a typo in one line: "processs_data" (extra 's')
        result = await tool.run(
            file_path="fuzzy.py",
            old_string=(
                "import os\n"
                "import sys\n"
                "\n"
                "def processs_data():\n"
                "    data = load_file()\n"
                "    result = transform(data)\n"
                "    logger.info(result)\n"
                "    return result\n"
            ),
            new_string=(
                "import os\n"
                "import sys\n"
                "\n"
                "def process_v2():\n"
                "    data = load_file()\n"
                "    result = transform(data)\n"
                "    logger.info(result)\n"
                "    return result\n"
            ),
        )
        assert result.success, f"Tool error: {result.error}"
        assert result.metadata["match_strategy"] == "difflib"
        assert result.metadata["match_confidence"] >= 0.85

    @pytest.mark.asyncio
    async def test_too_different_fails(self, tool, tmp_path):
        """Completely different content should not fuzzy match."""
        (tmp_path / "nope.py").write_text("def alpha():\n    return 1\n")
        result = await tool.run(
            file_path="nope.py",
            old_string="class Beta:\n    pass\n    something_else_entirely\n",
            new_string="class Gamma:\n    pass\n",
        )
        assert not result.success
        assert "not found" in result.error.lower()


# ── Diff Output ──────────────────────────────────────────────────────


class TestDiffOutput:
    @pytest.mark.asyncio
    async def test_diff_included_in_metadata(self, tool, sample_file):
        result = await tool.run(
            file_path=sample_file,
            old_string='print("Hello, world!")',
            new_string='print("Hi, world!")',
        )
        assert result.success
        diff = result.metadata.get("diff", "")
        assert "---" in diff
        assert "+++" in diff
        assert "-" in diff  # removed line
        assert "+" in diff  # added line


# ── Atomic Write Safety ──────────────────────────────────────────────


class TestAtomicWrite:
    @pytest.mark.asyncio
    async def test_no_tmp_file_left_behind(self, tool, sample_file):
        await tool.run(
            file_path=sample_file,
            old_string='print("Hello, world!")',
            new_string='print("Hi, world!")',
        )
        # No .tmp file should remain
        tmp_file = os.path.join(tool.working_dir, sample_file + ".tmp")
        assert not os.path.exists(tmp_file)

    @pytest.mark.asyncio
    async def test_unicode_content(self, tool, tmp_path):
        """Ensure Unicode content is handled correctly."""
        (tmp_path / "unicode.py").write_text('msg = "日本語テスト"\n', encoding="utf-8")
        result = await tool.run(
            file_path="unicode.py",
            old_string='msg = "日本語テスト"',
            new_string='msg = "中文测试"',
        )
        assert result.success
        content = (tmp_path / "unicode.py").read_text(encoding="utf-8")
        assert '中文测试' in content
