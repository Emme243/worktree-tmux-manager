"""Tests for tt_tmux.screens.__init__ — public API exports."""

from __future__ import annotations

from tt_tmux.screens import WorktreeListScreen


class TestScreensExports:
    def test_exports_worktree_list_screen(self):
        assert WorktreeListScreen is not None

    def test_all_contains_expected_names(self):
        import tt_tmux.screens as mod

        assert set(mod.__all__) == {"WorktreeListScreen"}
