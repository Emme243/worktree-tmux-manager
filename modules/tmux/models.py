"""Tmux data models."""

from __future__ import annotations

from dataclasses import dataclass, field


class TmuxError(Exception):
    """Raised when a tmux command fails."""


@dataclass
class WindowConfig:
    """Configuration for a single tmux window."""

    name: str
    command: str
    working_dir: str


@dataclass
class SessionConfig:
    """Configuration for a tmux session."""

    name: str
    windows: list[WindowConfig] = field(default_factory=list)
    default_window: str = "editor"
