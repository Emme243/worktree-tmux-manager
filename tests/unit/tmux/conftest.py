"""Shared fixtures for tmux tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from modules.tmux.models import SessionConfig, WindowConfig


# ---------------------------------------------------------------------------
# Mock _run_tmux — the single subprocess gateway
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_run_tmux():
    """Patch ``_run_tmux`` in the operations module.

    Returns a MagicMock whose ``return_value`` defaults to a successful
    CompletedProcess-like object (returncode=0, stdout="", stderr="").
    """
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""

    with patch(
        "modules.tmux.operations._run_tmux",
        return_value=result,
    ) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Sample configs
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_window_config() -> WindowConfig:
    return WindowConfig(name="editor", command="nvim .", working_dir="/repo")


@pytest.fixture
def sample_session_config() -> SessionConfig:
    return SessionConfig(
        name="tt-my-feature",
        windows=[
            WindowConfig(name="editor", command="nvim .", working_dir="/repo"),
            WindowConfig(name="claude", command="claude", working_dir="/repo"),
            WindowConfig(
                name="serve",
                command="npm install && npm run serve",
                working_dir="/repo/frontend",
            ),
        ],
        default_window="editor",
    )
