"""Tests for modules.screens.__init__ — public API exports."""

from __future__ import annotations

from modules.screens import ProjectSetupScreen, WorktreeListScreen


class TestScreensExports:
    def test_exports_worktree_list_screen(self):
        assert WorktreeListScreen is not None

    def test_exports_project_setup_screen(self):
        assert ProjectSetupScreen is not None

    def test_all_contains_expected_names(self):
        import modules.screens as mod

        assert set(mod.__all__) == {"ProjectSetupScreen", "WorktreeListScreen"}
