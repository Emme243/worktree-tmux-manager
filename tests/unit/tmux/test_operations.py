"""Tests for modules.tmux.operations — tmux subprocess operations."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from modules.git.models import WorktreeInfo
from modules.tmux.models import SessionConfig, TmuxError, WindowConfig
from modules.tmux.operations import (
    _attach_session,
    _create_session,
    _run_tmux,
    _sanitize_session_name,
    build_session_config,
    enter_worktree_session,
    is_inside_tmux,
    is_worktree_session_active,
    session_exists,
)


# ---------------------------------------------------------------------------
# _run_tmux — subprocess gateway
# ---------------------------------------------------------------------------


class TestRunTmux:
    def test_success_returns_completed_process(self):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "output"
        with patch("subprocess.run", return_value=result) as mock_run:
            ret = _run_tmux("list-sessions")
            mock_run.assert_called_once_with(
                ["tmux", "list-sessions"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert ret is result

    def test_passes_check_false(self):
        result = MagicMock()
        result.returncode = 1
        with patch("subprocess.run", return_value=result) as mock_run:
            _run_tmux("has-session", "-t", "foo", check=False)
            mock_run.assert_called_once_with(
                ["tmux", "has-session", "-t", "foo"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_file_not_found_raises_tmux_error(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(TmuxError, match="not installed"):
                _run_tmux("list-sessions")

    def test_called_process_error_raises_tmux_error_with_stderr(self):
        exc = subprocess.CalledProcessError(1, "tmux", stderr="bad session\n")
        with patch("subprocess.run", side_effect=exc):
            with pytest.raises(TmuxError, match="bad session"):
                _run_tmux("has-session", "-t", "bad")

    def test_called_process_error_empty_stderr_fallback(self):
        exc = subprocess.CalledProcessError(1, "tmux", stderr="")
        with patch("subprocess.run", side_effect=exc):
            with pytest.raises(TmuxError, match="tmux has-session failed"):
                _run_tmux("has-session", "-t", "x")

    def test_multiple_args_passed_correctly(self):
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result) as mock_run:
            _run_tmux("send-keys", "-t", "sess:win", "echo hi", "C-m")
            expected = ["tmux", "send-keys", "-t", "sess:win", "echo hi", "C-m"]
            mock_run.assert_called_once_with(
                expected,
                capture_output=True,
                text=True,
                check=True,
            )


# ---------------------------------------------------------------------------
# session_exists
# ---------------------------------------------------------------------------


class TestSessionExists:
    def test_returns_true_when_exists(self, mock_run_tmux):
        mock_run_tmux.return_value.returncode = 0
        assert session_exists("my-session") is True
        mock_run_tmux.assert_called_once_with(
            "has-session", "-t", "my-session", check=False
        )

    def test_returns_false_when_not_exists(self, mock_run_tmux):
        mock_run_tmux.return_value.returncode = 1
        assert session_exists("no-session") is False


# ---------------------------------------------------------------------------
# _create_session
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_creates_session_with_first_window(self, mock_run_tmux):
        config = SessionConfig(
            name="tt-feat",
            windows=[
                WindowConfig(name="editor", command="nvim", working_dir="/repo"),
            ],
            default_window="editor",
        )
        _create_session(config)
        calls = mock_run_tmux.call_args_list
        # new-session
        assert calls[0] == call(
            "new-session", "-d", "-s", "tt-feat", "-n", "editor", "-c", "/repo"
        )
        # send-keys for first window
        assert calls[1] == call(
            "send-keys", "-t", "tt-feat:editor", "nvim", "C-m"
        )
        # select-window
        assert calls[2] == call(
            "select-window", "-t", "tt-feat:editor"
        )

    def test_creates_additional_windows(self, mock_run_tmux, sample_session_config):
        _create_session(sample_session_config)
        calls = mock_run_tmux.call_args_list
        # first window: new-session + send-keys = 2
        # rest windows: (new-window + send-keys) * 2 = 4
        # select-window = 1
        # total = 7
        assert len(calls) == 7

    def test_additional_window_commands(self, mock_run_tmux, sample_session_config):
        _create_session(sample_session_config)
        calls = mock_run_tmux.call_args_list
        # Second window (claude) — calls[2] is new-window, calls[3] is send-keys
        assert calls[2] == call(
            "new-window", "-t", "tt-my-feature",
            "-n", "claude", "-c", "/repo"
        )
        assert calls[3] == call(
            "send-keys", "-t", "tt-my-feature:claude", "claude", "C-m"
        )
        # Third window (serve) — calls[4] is new-window, calls[5] is send-keys
        assert calls[4] == call(
            "new-window", "-t", "tt-my-feature",
            "-n", "serve", "-c", "/repo/frontend"
        )
        assert calls[5] == call(
            "send-keys", "-t", "tt-my-feature:serve",
            "npm install && npm run serve", "C-m"
        )

    def test_selects_default_window(self, mock_run_tmux, sample_session_config):
        _create_session(sample_session_config)
        last_call = mock_run_tmux.call_args_list[-1]
        assert last_call == call(
            "select-window", "-t", "tt-my-feature:editor"
        )


# ---------------------------------------------------------------------------
# is_inside_tmux
# ---------------------------------------------------------------------------


class TestIsInsideTmux:
    def test_returns_true_when_tmux_env_set(self):
        with patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,12345,0"}):
            assert is_inside_tmux() is True

    def test_returns_false_when_tmux_env_unset(self):
        with patch.dict("os.environ", {}, clear=True):
            assert is_inside_tmux() is False

    def test_returns_false_when_tmux_env_empty(self):
        with patch.dict("os.environ", {"TMUX": ""}):
            assert is_inside_tmux() is False


# ---------------------------------------------------------------------------
# _attach_session
# ---------------------------------------------------------------------------


class TestAttachSession:
    def test_switches_client_when_inside_tmux(self, mock_run_tmux):
        with patch(
            "modules.tmux.operations.is_inside_tmux", return_value=True
        ):
            _attach_session("my-session")
            mock_run_tmux.assert_called_once_with(
                "switch-client", "-t", "my-session"
            )

    def test_attaches_session_when_outside_tmux(self, mock_run_tmux):
        with patch(
            "modules.tmux.operations.is_inside_tmux", return_value=False
        ):
            _attach_session("my-session")
            mock_run_tmux.assert_called_once_with(
                "attach-session", "-t", "my-session"
            )


# ---------------------------------------------------------------------------
# _sanitize_session_name
# ---------------------------------------------------------------------------


class TestSanitizeSessionName:
    def test_replaces_dots(self):
        assert _sanitize_session_name("my.feature") == "my-feature"

    def test_replaces_colons(self):
        assert _sanitize_session_name("feat:login") == "feat-login"

    def test_replaces_multiple_dots_and_colons(self):
        assert _sanitize_session_name("a.b:c.d") == "a-b-c-d"

    def test_no_change_for_clean_name(self):
        assert _sanitize_session_name("my-feature") == "my-feature"

    def test_empty_string(self):
        assert _sanitize_session_name("") == ""

    def test_preserves_slashes_and_underscores(self):
        assert _sanitize_session_name("feat/login_v2") == "feat/login_v2"


# ---------------------------------------------------------------------------
# build_session_config
# ---------------------------------------------------------------------------


class TestBuildSessionConfig:
    def test_session_name_prefixed_with_tt(self):
        wt = WorktreeInfo(path="/home/user/repos/my-feature")
        config = build_session_config(wt)
        assert config.name == "tt-my-feature"

    def test_session_name_sanitized(self):
        wt = WorktreeInfo(path="/home/user/repos/my.feature")
        config = build_session_config(wt)
        assert config.name == "tt-my-feature"

    def test_has_three_windows(self):
        wt = WorktreeInfo(path="/home/user/repos/feat")
        config = build_session_config(wt)
        assert len(config.windows) == 3

    def test_editor_window(self):
        wt = WorktreeInfo(path="/home/user/repos/feat")
        config = build_session_config(wt)
        editor = config.windows[0]
        assert editor.name == "editor"
        assert editor.command == "nvim ."
        assert editor.working_dir == "/home/user/repos/feat"

    def test_claude_window(self):
        wt = WorktreeInfo(path="/home/user/repos/feat")
        config = build_session_config(wt)
        claude = config.windows[1]
        assert claude.name == "claude"
        assert claude.command == "claude"
        assert claude.working_dir == "/home/user/repos/feat"

    def test_serve_window_uses_frontend_subdir(self):
        wt = WorktreeInfo(path="/home/user/repos/feat")
        config = build_session_config(wt)
        serve = config.windows[2]
        assert serve.name == "serve"
        assert "npm" in serve.command
        assert serve.working_dir == "/home/user/repos/feat/frontend"

    def test_default_window_is_editor(self):
        wt = WorktreeInfo(path="/home/user/repos/feat")
        config = build_session_config(wt)
        assert config.default_window == "editor"


# ---------------------------------------------------------------------------
# is_worktree_session_active
# ---------------------------------------------------------------------------


class TestIsWorktreeSessionActive:
    def test_checks_correct_session_name(self, mock_run_tmux):
        mock_run_tmux.return_value.returncode = 0
        result = is_worktree_session_active("my-feature")
        mock_run_tmux.assert_called_once_with(
            "has-session", "-t", "tt-my-feature", check=False
        )
        assert result is True

    def test_returns_false_when_no_session(self, mock_run_tmux):
        mock_run_tmux.return_value.returncode = 1
        assert is_worktree_session_active("nope") is False

    def test_sanitizes_worktree_name(self, mock_run_tmux):
        mock_run_tmux.return_value.returncode = 0
        is_worktree_session_active("my.feature")
        mock_run_tmux.assert_called_once_with(
            "has-session", "-t", "tt-my-feature", check=False
        )


# ---------------------------------------------------------------------------
# enter_worktree_session
# ---------------------------------------------------------------------------


class TestEnterWorktreeSession:
    def test_creates_and_attaches_when_new(self, mock_run_tmux):
        mock_run_tmux.return_value.returncode = 1  # session doesn't exist
        config = SessionConfig(
            name="tt-feat",
            windows=[
                WindowConfig(name="editor", command="nvim", working_dir="/r"),
            ],
        )
        with patch(
            "modules.tmux.operations.session_exists", return_value=False
        ) as mock_exists, patch(
            "modules.tmux.operations._create_session"
        ) as mock_create, patch(
            "modules.tmux.operations._attach_session"
        ) as mock_attach:
            enter_worktree_session(config)
            mock_exists.assert_called_once_with("tt-feat")
            mock_create.assert_called_once_with(config)
            mock_attach.assert_called_once_with("tt-feat")

    def test_skips_create_when_exists(self, mock_run_tmux):
        config = SessionConfig(
            name="tt-feat",
            windows=[
                WindowConfig(name="editor", command="nvim", working_dir="/r"),
            ],
        )
        with patch(
            "modules.tmux.operations.session_exists", return_value=True
        ) as mock_exists, patch(
            "modules.tmux.operations._create_session"
        ) as mock_create, patch(
            "modules.tmux.operations._attach_session"
        ) as mock_attach:
            enter_worktree_session(config)
            mock_exists.assert_called_once_with("tt-feat")
            mock_create.assert_not_called()
            mock_attach.assert_called_once_with("tt-feat")
