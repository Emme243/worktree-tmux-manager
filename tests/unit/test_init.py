"""Tests for tt_tmux.__init__ — top-level package exports."""

from __future__ import annotations

from tt_tmux import GitWorktreeApp


class TestTopLevelExports:
    def test_exports_git_worktree_app(self):
        assert GitWorktreeApp is not None

    def test_all_contains_expected_names(self):
        import tt_tmux

        assert set(tt_tmux.__all__) == {"GitWorktreeApp"}

    def test_git_worktree_app_is_from_app_module(self):
        from tt_tmux.app import GitWorktreeApp as AppClass

        assert GitWorktreeApp is AppClass
