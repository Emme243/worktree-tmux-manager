"""Tests for modules.__init__ — top-level package exports."""

from __future__ import annotations

from modules import GitWorktreeApp


class TestTopLevelExports:
    def test_exports_git_worktree_app(self):
        assert GitWorktreeApp is not None

    def test_all_contains_expected_names(self):
        import modules

        assert set(modules.__all__) == {"GitWorktreeApp"}

    def test_git_worktree_app_is_from_app_module(self):
        from modules.app import GitWorktreeApp as AppClass

        assert GitWorktreeApp is AppClass
