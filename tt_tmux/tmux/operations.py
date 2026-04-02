"""Tmux session management operations.

All functions are synchronous because they run inside Textual's
``app.suspend()`` context manager, which is itself synchronous.
"""

from __future__ import annotations

import os
import re
import subprocess

from tt_tmux.git.models import WorktreeInfo

from .models import SessionConfig, TmuxError, WindowConfig


def _run_tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a tmux command and return the result."""
    try:
        return subprocess.run(
            ["tmux", *args],
            capture_output=True,
            text=True,
            check=check,
        )
    except FileNotFoundError:
        raise TmuxError("tmux is not installed or not in PATH") from None
    except subprocess.CalledProcessError as exc:
        raise TmuxError(exc.stderr.strip() or f"tmux {args[0]} failed") from None


def session_exists(session_name: str) -> bool:
    """Check if a tmux session already exists."""
    result = _run_tmux("has-session", "-t", session_name, check=False)
    return result.returncode == 0


def _create_session(config: SessionConfig) -> None:
    """Create a new tmux session with the configured windows."""
    first, *rest = config.windows

    _run_tmux(
        "new-session", "-d",
        "-s", config.name,
        "-n", first.name,
        "-c", first.working_dir,
    )
    _run_tmux("send-keys", "-t", f"{config.name}:{first.name}", first.command, "C-m")

    for win in rest:
        _run_tmux(
            "new-window",
            "-t", config.name,
            "-n", win.name,
            "-c", win.working_dir,
        )
        _run_tmux("send-keys", "-t", f"{config.name}:{win.name}", win.command, "C-m")

    _run_tmux("select-window", "-t", f"{config.name}:{config.default_window}")


def is_inside_tmux() -> bool:
    """Return True if the current process is running inside tmux."""
    return bool(os.environ.get("TMUX"))


def _attach_session(session_name: str) -> None:
    """Attach or switch to the tmux session."""
    if is_inside_tmux():
        _run_tmux("switch-client", "-t", session_name)
    else:
        _run_tmux("attach-session", "-t", session_name)


def _sanitize_session_name(name: str) -> str:
    """Sanitize a name for use as a tmux session name.

    Tmux session names cannot contain dots or colons.
    """
    return re.sub(r"[.:]", "-", name)


def build_session_config(worktree: WorktreeInfo) -> SessionConfig:
    """Build a tmux session config from a worktree."""
    session_name = f"tt-{_sanitize_session_name(worktree.name)}"
    wt_path = worktree.path
    frontend_path = os.path.join(wt_path, "frontend")

    return SessionConfig(
        name=session_name,
        windows=[
            WindowConfig(name="editor", command="nvim .", working_dir=wt_path),
            WindowConfig(name="claude", command="claude", working_dir=wt_path),
            WindowConfig(
                name="serve",
                command="npm install && npm run serve",
                working_dir=frontend_path,
            ),
        ],
        default_window="editor",
    )


def is_worktree_session_active(wt_name: str) -> bool:
    """Check if a tmux session exists for the given worktree name."""
    return session_exists(f"tt-{_sanitize_session_name(wt_name)}")


def enter_worktree_session(config: SessionConfig) -> None:
    """Create a tmux session if needed, then attach to it."""
    if not session_exists(config.name):
        _create_session(config)
    _attach_session(config.name)
