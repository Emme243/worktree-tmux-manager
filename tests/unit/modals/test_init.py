"""Tests for tt_tmux.modals.__init__ — public API exports."""

from __future__ import annotations

from tt_tmux.modals import (
    AddWorktreeModal,
    RemoveWorktreeModal,
    RenameWorktreeModal,
)


class TestModalsExports:
    def test_exports_add_worktree_modal(self):
        assert AddWorktreeModal is not None

    def test_exports_remove_worktree_modal(self):
        assert RemoveWorktreeModal is not None

    def test_exports_rename_worktree_modal(self):
        assert RenameWorktreeModal is not None

    def test_all_contains_expected_names(self):
        import tt_tmux.modals as mod

        assert set(mod.__all__) == {
            "AddWorktreeModal",
            "RemoveWorktreeModal",
            "RenameWorktreeModal",
        }
