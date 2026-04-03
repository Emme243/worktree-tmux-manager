"""Tests for modules.git.models — pure dataclass and property tests."""

from __future__ import annotations

import pytest

from modules.git.models import GitError, WorkingTreeStatus, WorktreeInfo

# ---------------------------------------------------------------------------
# GitError
# ---------------------------------------------------------------------------


class TestGitError:
    def test_is_exception_subclass(self):
        assert issubclass(GitError, Exception)

    def test_preserves_message(self):
        err = GitError("fatal: not a git repository")
        assert str(err) == "fatal: not a git repository"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(GitError, match="something went wrong"):
            raise GitError("something went wrong")


# ---------------------------------------------------------------------------
# WorkingTreeStatus
# ---------------------------------------------------------------------------


class TestWorkingTreeStatusDefaults:
    def test_all_fields_default_to_zero(self):
        status = WorkingTreeStatus()
        assert status.staged == 0
        assert status.modified == 0
        assert status.untracked == 0
        assert status.conflicted == 0


class TestWorkingTreeStatusIsClean:
    def test_clean_when_all_zero(self):
        assert WorkingTreeStatus().is_clean is True

    @pytest.mark.parametrize(
        "field",
        ["staged", "modified", "untracked", "conflicted"],
        ids=["staged", "modified", "untracked", "conflicted"],
    )
    def test_not_clean_when_any_field_nonzero(self, field: str):
        status = WorkingTreeStatus(**{field: 1})
        assert status.is_clean is False

    def test_not_clean_when_multiple_fields_nonzero(self):
        status = WorkingTreeStatus(staged=1, modified=2)
        assert status.is_clean is False


class TestWorkingTreeStatusSummary:
    def test_clean_summary(self):
        assert WorkingTreeStatus().summary == "clean"

    def test_staged_only(self):
        assert WorkingTreeStatus(staged=3).summary == "3S"

    def test_modified_only(self):
        assert WorkingTreeStatus(modified=2).summary == "2M"

    def test_untracked_only(self):
        assert WorkingTreeStatus(untracked=5).summary == "5?"

    def test_conflicted_only(self):
        assert WorkingTreeStatus(conflicted=1).summary == "1!"

    def test_all_categories_in_order(self):
        status = WorkingTreeStatus(staged=1, modified=2, untracked=3, conflicted=4)
        assert status.summary == "1S 2M 3? 4!"

    def test_partial_mix_skips_zero_fields(self):
        status = WorkingTreeStatus(staged=2, untracked=1)
        assert status.summary == "2S 1?"

    def test_large_counts(self):
        status = WorkingTreeStatus(staged=100, modified=50)
        assert status.summary == "100S 50M"


# ---------------------------------------------------------------------------
# WorktreeInfo
# ---------------------------------------------------------------------------


class TestWorktreeInfoDefaults:
    def test_all_defaults(self):
        wt = WorktreeInfo()
        assert wt.path == ""
        assert wt.head == ""
        assert wt.branch == ""
        assert wt.is_bare is False
        assert wt.is_detached is False
        assert wt.locked is False
        assert wt.lock_reason == ""
        assert wt.prunable is False
        assert wt.wt_status is None


class TestWorktreeInfoName:
    def test_extracts_basename_from_path(self):
        wt = WorktreeInfo(path="/home/user/repos/feature-x")
        assert wt.name == "feature-x"

    def test_empty_path_returns_empty_string(self):
        wt = WorktreeInfo(path="")
        assert wt.name == ""

    def test_root_path(self):
        wt = WorktreeInfo(path="/")
        assert wt.name == ""

    def test_nested_deep_path(self):
        wt = WorktreeInfo(path="/a/b/c/d/my-worktree")
        assert wt.name == "my-worktree"


class TestWorktreeInfoStatus:
    def test_active_by_default(self):
        assert WorktreeInfo().status == "active"

    def test_bare(self):
        assert WorktreeInfo(is_bare=True).status == "bare"

    def test_locked_without_reason(self):
        assert WorktreeInfo(locked=True).status == "locked"

    def test_locked_with_reason(self):
        wt = WorktreeInfo(locked=True, lock_reason="WIP")
        assert wt.status == "locked (WIP)"

    def test_prunable(self):
        assert WorktreeInfo(prunable=True).status == "prunable"

    def test_multiple_flags_combined(self):
        wt = WorktreeInfo(is_bare=True, locked=True, prunable=True)
        assert wt.status == "bare, locked, prunable"

    def test_bare_and_locked_with_reason(self):
        wt = WorktreeInfo(is_bare=True, locked=True, lock_reason="archive")
        assert wt.status == "bare, locked (archive)"


class TestWorktreeInfoWtStatusDisplay:
    def test_bare_shows_dash(self):
        wt = WorktreeInfo(is_bare=True)
        assert wt.wt_status_display == "-"

    def test_none_status_shows_ellipsis(self):
        wt = WorktreeInfo(wt_status=None)
        assert wt.wt_status_display == "..."

    def test_clean_status(self):
        wt = WorktreeInfo(wt_status=WorkingTreeStatus())
        assert wt.wt_status_display == "clean"

    def test_dirty_status_delegates_to_summary(self):
        wt = WorktreeInfo(wt_status=WorkingTreeStatus(staged=1, modified=2))
        assert wt.wt_status_display == "1S 2M"

    def test_bare_takes_precedence_over_wt_status(self):
        wt = WorktreeInfo(
            is_bare=True,
            wt_status=WorkingTreeStatus(staged=5),
        )
        assert wt.wt_status_display == "-"
