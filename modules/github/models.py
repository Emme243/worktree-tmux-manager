"""GitHub domain models — PullRequest, Comment, PRState."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PRState(StrEnum):
    """GitHub pull request state values."""

    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    DRAFT = "draft"


@dataclass
class PullRequest:
    """A GitHub pull request with all fields needed by the TUI dashboard."""

    number: int
    title: str
    state: PRState
    url: str
    head_branch: str
    base_branch: str
    merged: bool
    draft: bool
    updated_at: datetime
    unread_comment_count: int = field(default=0)


@dataclass
class Comment:
    """A GitHub pull request comment (general or inline review comment)."""

    id: int
    body: str
    author: str
    created_at: datetime
    is_read: bool = field(default=False)
