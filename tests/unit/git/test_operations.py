"""Tests for modules.git.operations — parsing functions and async git commands."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.git.models import GitError, WorkingTreeStatus, WorktreeInfo
from modules.git.operations import (
    add_worktree,
    get_worktree_status,
    is_git_repo,
    list_branches,
    list_worktrees,
    lock_worktree,
    move_worktree,
    parse_status_porcelain,
    parse_worktree_porcelain,
    populate_worktree_statuses,
    prune_worktrees,
    remove_worktree,
    repair_worktrees,
    run_git,
    unlock_worktree,
)

# ===========================================================================
# parse_worktree_porcelain — sync, real data, no mocks
# ===========================================================================


class TestParseWorktreePorcelain:
    def test_empty_string_returns_empty_list(self):
        assert parse_worktree_porcelain("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert parse_worktree_porcelain("   \n\n  ") == []

    def test_single_normal_worktree(self):
        output = (
            "worktree /home/user/repo\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "branch refs/heads/main\n"
        )
        result = parse_worktree_porcelain(output)
        assert len(result) == 1
        wt = result[0]
        assert wt.path == "/home/user/repo"
        assert wt.head == "abc12345"
        assert wt.branch == "main"
        assert wt.is_bare is False
        assert wt.is_detached is False

    def test_bare_worktree(self):
        output = (
            "worktree /home/user/repo.git\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "bare\n"
        )
        result = parse_worktree_porcelain(output)
        assert len(result) == 1
        assert result[0].is_bare is True
        assert result[0].branch == "(bare)"

    def test_detached_head(self):
        output = (
            "worktree /home/user/repo-detached\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "detached\n"
        )
        result = parse_worktree_porcelain(output)
        assert len(result) == 1
        assert result[0].is_detached is True
        assert result[0].branch == "(detached)"

    def test_locked_without_reason(self):
        output = (
            "worktree /home/user/repo-locked\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "branch refs/heads/dev\n"
            "locked\n"
        )
        result = parse_worktree_porcelain(output)
        assert result[0].locked is True
        assert result[0].lock_reason == ""

    def test_locked_with_reason(self):
        output = (
            "worktree /home/user/repo-locked\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "branch refs/heads/dev\n"
            "locked work in progress\n"
        )
        result = parse_worktree_porcelain(output)
        assert result[0].locked is True
        assert result[0].lock_reason == "work in progress"

    def test_prunable(self):
        output = (
            "worktree /home/user/repo-prunable\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "branch refs/heads/stale\n"
            "prunable\n"
        )
        result = parse_worktree_porcelain(output)
        assert result[0].prunable is True

    def test_multiple_worktrees(self, sample_porcelain_output):
        result = parse_worktree_porcelain(sample_porcelain_output)
        assert len(result) == 4

        assert result[0].branch == "main"
        assert result[1].branch == "feature/login"
        assert result[2].is_bare is True
        assert result[3].locked is True
        assert result[3].lock_reason == "work in progress"

    def test_head_truncated_to_8_chars(self):
        full_hash = "a" * 40
        output = f"worktree /repo\nHEAD {full_hash}\nbranch refs/heads/main\n"
        result = parse_worktree_porcelain(output)
        assert result[0].head == "aaaaaaaa"
        assert len(result[0].head) == 8

    def test_branch_strips_refs_heads_prefix(self):
        output = (
            "worktree /repo\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "branch refs/heads/feature/my-branch\n"
        )
        result = parse_worktree_porcelain(output)
        assert result[0].branch == "feature/my-branch"


# ===========================================================================
# parse_status_porcelain — sync, real data, no mocks
# ===========================================================================


class TestParseStatusPorcelain:
    def test_empty_string_returns_clean_status(self):
        status = parse_status_porcelain("")
        assert status.is_clean is True
        assert status.staged == 0
        assert status.modified == 0
        assert status.untracked == 0
        assert status.conflicted == 0

    def test_untracked_files(self):
        output = "?? file1.txt\n?? file2.txt\n?? dir/file3.txt\n"
        status = parse_status_porcelain(output)
        assert status.untracked == 3
        assert status.staged == 0
        assert status.modified == 0

    @pytest.mark.parametrize(
        "index_code",
        ["A", "M", "D", "R", "C"],
        ids=["added", "modified", "deleted", "renamed", "copied"],
    )
    def test_staged_index_codes(self, index_code: str):
        output = f"{index_code}  file.txt\n"
        status = parse_status_porcelain(output)
        assert status.staged == 1

    def test_worktree_modified(self):
        output = " M file.txt\n"
        status = parse_status_porcelain(output)
        assert status.modified == 1
        assert status.staged == 0

    def test_worktree_deleted(self):
        output = " D file.txt\n"
        status = parse_status_porcelain(output)
        assert status.modified == 1

    def test_both_staged_and_modified(self):
        output = "MM file.txt\n"
        status = parse_status_porcelain(output)
        assert status.staged == 1
        assert status.modified == 1

    @pytest.mark.parametrize(
        "codes",
        ["UU", "AA", "DD", "AU", "UA", "DU", "UD"],
        ids=["UU", "AA", "DD", "AU", "UA", "DU", "UD"],
    )
    def test_conflict_codes(self, codes: str):
        output = f"{codes} file.txt\n"
        status = parse_status_porcelain(output)
        assert status.conflicted == 1

    def test_ignored_files_not_counted(self):
        output = "!! ignored.pyc\n!! __pycache__/\n"
        status = parse_status_porcelain(output)
        assert status.is_clean is True

    def test_short_line_ignored(self):
        output = "X\n"
        status = parse_status_porcelain(output)
        assert status.is_clean is True

    def test_mixed_realistic_output(self, sample_status_output):
        status = parse_status_porcelain(sample_status_output)
        # M  staged_file.py     → staged=1
        # A  new_file.py        → staged=2
        # MM both_file.py       → staged=3, modified=1
        #  M modified_file.py   → modified=2
        # ?? untracked1.txt     → untracked=1
        # ?? untracked2.txt     → untracked=2
        # UU conflict_file.py   → conflicted=1
        # !! ignored_file.pyc   → ignored
        assert status.staged == 3
        assert status.modified == 2
        assert status.untracked == 2
        assert status.conflicted == 1

    def test_multiple_unrelated_files(self):
        output = "A  src/new.py\n M src/old.py\n?? TODO.md\n"
        status = parse_status_porcelain(output)
        assert status.staged == 1
        assert status.modified == 1
        assert status.untracked == 1
        assert status.conflicted == 0


# ===========================================================================
# run_git — async, mock subprocess
# ===========================================================================


class TestRunGit:
    async def test_success_returns_stdout(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"output text\n", b""))

        with patch(
            "modules.git.operations.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ):
            result = await run_git("/repo", "status")
            assert result == "output text\n"

    async def test_failure_raises_git_error_with_stderr(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"fatal: not a git repository")
        )

        with (
            patch(
                "modules.git.operations.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
                return_value=mock_proc,
            ),
            pytest.raises(GitError, match="fatal: not a git repository"),
        ):
            await run_git("/repo", "status")

    async def test_failure_with_empty_stderr_shows_unknown_error(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch(
                "modules.git.operations.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
                return_value=mock_proc,
            ),
            pytest.raises(GitError, match="Unknown git error"),
        ):
            await run_git("/repo", "status")

    async def test_passes_correct_args_to_subprocess(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "modules.git.operations.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ) as mock_exec:
            await run_git("/my/repo", "worktree", "list", "--porcelain")
            mock_exec.assert_called_once_with(
                "git",
                "-C",
                "/my/repo",
                "worktree",
                "list",
                "--porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )


# ===========================================================================
# is_git_repo — async, mock run_git
# ===========================================================================


class TestIsGitRepo:
    async def test_returns_true_when_run_git_succeeds(self, mock_run_git):
        mock_run_git.return_value = "/repo/.git"
        result = await is_git_repo("/repo")
        assert result is True
        mock_run_git.assert_called_once_with("/repo", "rev-parse", "--git-dir")

    async def test_returns_false_when_run_git_raises(self, mock_run_git):
        mock_run_git.side_effect = GitError("not a repo")
        result = await is_git_repo("/not-a-repo")
        assert result is False


# ===========================================================================
# list_worktrees — async, mock run_git
# ===========================================================================


class TestListWorktrees:
    async def test_calls_run_git_with_correct_args(self, mock_run_git):
        mock_run_git.return_value = ""
        await list_worktrees("/repo")
        mock_run_git.assert_called_once_with("/repo", "worktree", "list", "--porcelain")

    async def test_returns_parsed_worktree_list(self, mock_run_git):
        mock_run_git.return_value = (
            "worktree /repo\n"
            "HEAD abc1234567890abcdef1234567890abcdef123456\n"
            "branch refs/heads/main\n"
        )
        result = await list_worktrees("/repo")
        assert len(result) == 1
        assert result[0].branch == "main"


# ===========================================================================
# get_worktree_status — async, mock run_git
# ===========================================================================


class TestGetWorktreeStatus:
    async def test_calls_run_git_with_correct_args(self, mock_run_git):
        mock_run_git.return_value = ""
        await get_worktree_status("/wt")
        mock_run_git.assert_called_once_with("/wt", "status", "--porcelain=v1")

    async def test_returns_parsed_status(self, mock_run_git):
        mock_run_git.return_value = "?? file.txt\nM  staged.py\n"
        result = await get_worktree_status("/wt")
        assert result.untracked == 1
        assert result.staged == 1


# ===========================================================================
# populate_worktree_statuses — async, mock get_worktree_status
# ===========================================================================


class TestPopulateWorktreeStatuses:
    async def test_sets_status_on_normal_worktrees(self):
        wt = WorktreeInfo(path="/repo/wt1", branch="main")
        expected_status = WorkingTreeStatus(staged=1)

        with patch(
            "modules.git.operations.get_worktree_status",
            new_callable=AsyncMock,
            return_value=expected_status,
        ):
            await populate_worktree_statuses([wt])

        assert wt.wt_status is expected_status

    async def test_skips_bare_worktrees(self):
        bare_wt = WorktreeInfo(path="/repo/bare", is_bare=True)

        with patch(
            "modules.git.operations.get_worktree_status",
            new_callable=AsyncMock,
        ) as mock_status:
            await populate_worktree_statuses([bare_wt])

        mock_status.assert_not_called()
        assert bare_wt.wt_status is None

    async def test_handles_git_error_gracefully(self):
        wt = WorktreeInfo(path="/repo/broken")

        with patch(
            "modules.git.operations.get_worktree_status",
            new_callable=AsyncMock,
            side_effect=GitError("status failed"),
        ):
            await populate_worktree_statuses([wt])

        assert wt.wt_status is None

    async def test_populates_multiple_worktrees_concurrently(self):
        wt1 = WorktreeInfo(path="/repo/wt1", branch="main")
        wt2 = WorktreeInfo(path="/repo/wt2", branch="dev")
        bare = WorktreeInfo(path="/repo/bare", is_bare=True)

        status1 = WorkingTreeStatus(staged=1)
        status2 = WorkingTreeStatus(modified=2)

        async def _fake_status(path: str) -> WorkingTreeStatus:
            return status1 if path == "/repo/wt1" else status2

        with patch(
            "modules.git.operations.get_worktree_status",
            new_callable=AsyncMock,
            side_effect=_fake_status,
        ):
            await populate_worktree_statuses([wt1, wt2, bare])

        assert wt1.wt_status is status1
        assert wt2.wt_status is status2
        assert bare.wt_status is None


# ===========================================================================
# list_branches — async, mock run_git
# ===========================================================================


class TestListBranches:
    async def test_returns_branch_list(self, mock_run_git):
        mock_run_git.return_value = "main\nfeature/login\ndev\n"
        result = await list_branches("/repo")
        assert result == ["main", "feature/login", "dev"]

    async def test_empty_output_returns_empty_list(self, mock_run_git):
        mock_run_git.return_value = ""
        result = await list_branches("/repo")
        assert result == []

    async def test_strips_whitespace(self, mock_run_git):
        mock_run_git.return_value = "  main \n\n  dev  \n"
        result = await list_branches("/repo")
        assert result == ["main", "dev"]

    async def test_calls_run_git_with_correct_args(self, mock_run_git):
        mock_run_git.return_value = ""
        await list_branches("/repo")
        mock_run_git.assert_called_once_with(
            "/repo", "branch", "-a", "--format=%(refname:short)"
        )


# ===========================================================================
# add_worktree — async, mock run_git
# ===========================================================================


class TestAddWorktree:
    async def test_basic_add(self, mock_run_git):
        mock_run_git.return_value = ""
        await add_worktree("/repo", "/path/to/wt")
        mock_run_git.assert_called_once_with("/repo", "worktree", "add", "/path/to/wt")

    async def test_with_existing_branch(self, mock_run_git):
        mock_run_git.return_value = ""
        await add_worktree("/repo", "/path/to/wt", branch="main")
        mock_run_git.assert_called_once_with(
            "/repo", "worktree", "add", "/path/to/wt", "main"
        )

    async def test_with_new_branch(self, mock_run_git):
        mock_run_git.return_value = ""
        await add_worktree("/repo", "/path/to/wt", new_branch="feature/new")
        mock_run_git.assert_called_once_with(
            "/repo", "worktree", "add", "-b", "feature/new", "/path/to/wt"
        )

    async def test_detached(self, mock_run_git):
        mock_run_git.return_value = ""
        await add_worktree("/repo", "/path/to/wt", detached=True)
        mock_run_git.assert_called_once_with(
            "/repo", "worktree", "add", "--detach", "/path/to/wt"
        )

    async def test_all_options_combined(self, mock_run_git):
        mock_run_git.return_value = ""
        await add_worktree(
            "/repo",
            "/path/to/wt",
            branch="origin/main",
            new_branch="local-main",
            detached=True,
        )
        mock_run_git.assert_called_once_with(
            "/repo",
            "worktree",
            "add",
            "-b",
            "local-main",
            "--detach",
            "/path/to/wt",
            "origin/main",
        )


# ===========================================================================
# remove_worktree — async, mock run_git
# ===========================================================================


class TestRemoveWorktree:
    async def test_basic_remove(self, mock_run_git):
        mock_run_git.return_value = ""
        await remove_worktree("/repo", "/wt")
        mock_run_git.assert_called_once_with("/repo", "worktree", "remove", "/wt")

    async def test_force_remove(self, mock_run_git):
        mock_run_git.return_value = ""
        await remove_worktree("/repo", "/wt", force=True)
        mock_run_git.assert_called_once_with(
            "/repo", "worktree", "remove", "--force", "/wt"
        )


# ===========================================================================
# move_worktree — async, mock run_git
# ===========================================================================


class TestMoveWorktree:
    async def test_move(self, mock_run_git):
        mock_run_git.return_value = ""
        await move_worktree("/repo", "/old/path", "/new/path")
        mock_run_git.assert_called_once_with(
            "/repo", "worktree", "move", "/old/path", "/new/path"
        )


# ===========================================================================
# lock_worktree — async, mock run_git
# ===========================================================================


class TestLockWorktree:
    async def test_lock_without_reason(self, mock_run_git):
        mock_run_git.return_value = ""
        await lock_worktree("/repo", "/wt")
        mock_run_git.assert_called_once_with("/repo", "worktree", "lock", "/wt")

    async def test_lock_with_reason(self, mock_run_git):
        mock_run_git.return_value = ""
        await lock_worktree("/repo", "/wt", reason="WIP")
        mock_run_git.assert_called_once_with(
            "/repo", "worktree", "lock", "--reason", "WIP", "/wt"
        )


# ===========================================================================
# unlock_worktree — async, mock run_git
# ===========================================================================


class TestUnlockWorktree:
    async def test_unlock(self, mock_run_git):
        mock_run_git.return_value = ""
        await unlock_worktree("/repo", "/wt")
        mock_run_git.assert_called_once_with("/repo", "worktree", "unlock", "/wt")


# ===========================================================================
# prune_worktrees — async, mock run_git
# ===========================================================================


class TestPruneWorktrees:
    async def test_prune(self, mock_run_git):
        mock_run_git.return_value = ""
        await prune_worktrees("/repo")
        mock_run_git.assert_called_once_with("/repo", "worktree", "prune", "--verbose")


# ===========================================================================
# repair_worktrees — async, mock run_git
# ===========================================================================


class TestRepairWorktrees:
    async def test_repair(self, mock_run_git):
        mock_run_git.return_value = ""
        await repair_worktrees("/repo")
        mock_run_git.assert_called_once_with("/repo", "worktree", "repair")
