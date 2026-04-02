"""Tests for tt_tmux.tmux.models — TmuxError, WindowConfig, SessionConfig."""

from __future__ import annotations

import pytest

from tt_tmux.tmux.models import SessionConfig, TmuxError, WindowConfig


# ---------------------------------------------------------------------------
# TmuxError
# ---------------------------------------------------------------------------


class TestTmuxError:
    def test_is_exception(self):
        assert issubclass(TmuxError, Exception)

    def test_preserves_message(self):
        err = TmuxError("tmux not found")
        assert str(err) == "tmux not found"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(TmuxError, match="boom"):
            raise TmuxError("boom")


# ---------------------------------------------------------------------------
# WindowConfig
# ---------------------------------------------------------------------------


class TestWindowConfig:
    def test_stores_all_fields(self):
        wc = WindowConfig(name="editor", command="nvim .", working_dir="/repo")
        assert wc.name == "editor"
        assert wc.command == "nvim ."
        assert wc.working_dir == "/repo"

    def test_equality(self):
        a = WindowConfig(name="ed", command="vim", working_dir="/a")
        b = WindowConfig(name="ed", command="vim", working_dir="/a")
        assert a == b

    def test_inequality_on_different_name(self):
        a = WindowConfig(name="ed", command="vim", working_dir="/a")
        b = WindowConfig(name="shell", command="vim", working_dir="/a")
        assert a != b


# ---------------------------------------------------------------------------
# SessionConfig
# ---------------------------------------------------------------------------


class TestSessionConfig:
    def test_stores_name(self):
        sc = SessionConfig(name="my-session")
        assert sc.name == "my-session"

    def test_default_windows_empty(self):
        sc = SessionConfig(name="s")
        assert sc.windows == []

    def test_default_window_is_editor(self):
        sc = SessionConfig(name="s")
        assert sc.default_window == "editor"

    def test_custom_windows(self, sample_session_config):
        assert len(sample_session_config.windows) == 3
        assert sample_session_config.windows[0].name == "editor"
        assert sample_session_config.windows[1].name == "claude"
        assert sample_session_config.windows[2].name == "serve"

    def test_windows_list_is_independent(self):
        """Each SessionConfig gets its own windows list (no shared default)."""
        a = SessionConfig(name="a")
        b = SessionConfig(name="b")
        a.windows.append(WindowConfig(name="x", command="x", working_dir="/x"))
        assert len(b.windows) == 0

    def test_equality(self):
        a = SessionConfig(name="s", default_window="editor")
        b = SessionConfig(name="s", default_window="editor")
        assert a == b
