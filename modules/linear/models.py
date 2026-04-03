"""Linear domain models — Ticket, TicketStatus, TicketWorkflowState."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TicketStatus(str, Enum):
    """Linear issue status values."""

    NOT_STARTED = "NotStarted"
    IN_PROGRESS = "InProgress"
    IN_REVIEW = "InReview"
    DONE = "Done"
    CANCELLED = "Cancelled"


class TicketWorkflowState(str, Enum):
    """Dashboard grouping for the worktree list screen.

    Maps a combination of ticket status and local environment state to one of
    the four display groups shown in the TUI dashboard (see CLAUDE.md §3B).
    """

    NOT_STARTED = "Not Started"
    WORKTREE_CREATED = "Worktree Created"
    CODING_IN_PROGRESS = "Coding in Progress"
    UNDER_REVIEW = "Under Review"


@dataclass
class Ticket:
    """A Linear issue with all fields needed by the TUI dashboard."""

    id: str
    identifier: str
    title: str
    status: TicketStatus
    branch_name: str
    url: str
    updated_at: datetime
    assignee: str | None = None
    unread_comment_count: int = field(default=0)
