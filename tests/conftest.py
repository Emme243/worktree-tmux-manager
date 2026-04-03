"""Shared fixtures for all tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from modules.git.models import WorkingTreeStatus, WorktreeInfo


@pytest.fixture
def mock_run_git():
    """Patch ``modules.git.operations.run_git`` as an AsyncMock.

    Returns the mock so tests can configure ``.return_value`` or ``.side_effect``.
    """
    with patch("modules.git.operations.run_git", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def make_worktree_info():
    """Factory to create ``WorktreeInfo`` with sensible defaults."""

    def _make(**overrides) -> WorktreeInfo:
        defaults = {
            "path": "/home/user/repos/my-project",
            "head": "abc12345",
            "branch": "main",
        }
        defaults.update(overrides)
        return WorktreeInfo(**defaults)

    return _make


@pytest.fixture
def sample_porcelain_output() -> str:
    """Realistic ``git worktree list --porcelain`` output with multiple entries."""
    return (
        "worktree /home/user/repos/my-project\n"
        "HEAD abc1234567890abcdef1234567890abcdef123456\n"
        "branch refs/heads/main\n"
        "\n"
        "worktree /home/user/repos/my-project-feature\n"
        "HEAD def4567890abcdef1234567890abcdef12345678\n"
        "branch refs/heads/feature/login\n"
        "\n"
        "worktree /home/user/repos/my-project-bare\n"
        "HEAD 1234567890abcdef1234567890abcdef12345678\n"
        "bare\n"
        "\n"
        "worktree /home/user/repos/my-project-locked\n"
        "HEAD 9876543210abcdef1234567890abcdef12345678\n"
        "branch refs/heads/hotfix/urgent\n"
        "locked work in progress\n"
    )


@pytest.fixture
def sample_status_output() -> str:
    """Realistic ``git status --porcelain=v1`` output with mixed entries."""
    return (
        "M  staged_file.py\n"
        "A  new_file.py\n"
        " M modified_file.py\n"
        "MM both_file.py\n"
        "?? untracked1.txt\n"
        "?? untracked2.txt\n"
        "UU conflict_file.py\n"
        "!! ignored_file.pyc\n"
    )


@pytest.fixture
def clean_working_tree_status() -> WorkingTreeStatus:
    """A clean WorkingTreeStatus (all zeros)."""
    return WorkingTreeStatus()


@pytest.fixture
def dirty_working_tree_status() -> WorkingTreeStatus:
    """A dirty WorkingTreeStatus with values in all fields."""
    return WorkingTreeStatus(staged=2, modified=3, untracked=1, conflicted=1)
