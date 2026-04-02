"""Git data models."""

from __future__ import annotations

import os
from dataclasses import dataclass


class GitError(Exception):
    """Raised when a git command fails."""


@dataclass
class WorkingTreeStatus:
    """Counts of changed files in a worktree's working directory."""

    staged: int = 0
    modified: int = 0
    untracked: int = 0
    conflicted: int = 0

    @property
    def is_clean(self) -> bool:
        return not (self.staged or self.modified or self.untracked or self.conflicted)

    @property
    def summary(self) -> str:
        if self.is_clean:
            return "clean"
        parts: list[str] = []
        if self.staged:
            parts.append(f"{self.staged}S")
        if self.modified:
            parts.append(f"{self.modified}M")
        if self.untracked:
            parts.append(f"{self.untracked}?")
        if self.conflicted:
            parts.append(f"{self.conflicted}!")
        return " ".join(parts)


@dataclass
class WorktreeInfo:
    """Parsed info for a single worktree."""

    path: str = ""
    head: str = ""
    branch: str = ""
    is_bare: bool = False
    is_detached: bool = False
    locked: bool = False
    lock_reason: str = ""
    prunable: bool = False
    wt_status: WorkingTreeStatus | None = None

    @property
    def name(self) -> str:
        return os.path.basename(self.path) if self.path else ""

    @property
    def status(self) -> str:
        parts: list[str] = []
        if self.is_bare:
            parts.append("bare")
        if self.locked:
            reason = f" ({self.lock_reason})" if self.lock_reason else ""
            parts.append(f"locked{reason}")
        if self.prunable:
            parts.append("prunable")
        return ", ".join(parts) if parts else "active"

    @property
    def wt_status_display(self) -> str:
        if self.is_bare:
            return "-"
        if self.wt_status is None:
            return "..."
        return self.wt_status.summary
