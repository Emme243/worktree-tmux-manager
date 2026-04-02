"""Tests for tt_tmux.tmux.__init__ — public API exports."""

from __future__ import annotations

from tt_tmux.tmux import (
    SessionConfig,
    TmuxError,
    WindowConfig,
    build_session_config,
    enter_worktree_session,
    is_worktree_session_active,
)


class TestTmuxExports:
    def test_exports_tmux_error(self):
        assert TmuxError is not None

    def test_exports_session_config(self):
        assert SessionConfig is not None

    def test_exports_window_config(self):
        assert WindowConfig is not None

    def test_exports_build_session_config(self):
        assert callable(build_session_config)

    def test_exports_enter_worktree_session(self):
        assert callable(enter_worktree_session)

    def test_exports_is_worktree_session_active(self):
        assert callable(is_worktree_session_active)

    def test_all_contains_expected_names(self):
        import tt_tmux.tmux as mod

        assert set(mod.__all__) == {
            "SessionConfig",
            "TmuxError",
            "WindowConfig",
            "build_session_config",
            "enter_worktree_session",
            "is_worktree_session_active",
        }
