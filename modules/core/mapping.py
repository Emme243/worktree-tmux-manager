"""Branch ↔ Ticket and Worktree ↔ PR mapping utilities."""

from __future__ import annotations

from dataclasses import dataclass

from modules.git.models import WorktreeInfo
from modules.github.models import PRState, PullRequest
from modules.linear.models import Ticket, TicketStatus, TicketWorkflowState


def _normalize_branch(branch: str) -> str:
    """Strip refs/heads/ prefix for consistent branch name comparison."""
    return branch.removeprefix("refs/heads/")


def classify_workflow_state(
    worktree: WorktreeInfo | None,
    ticket: Ticket | None,
    pr: PullRequest | None,
) -> TicketWorkflowState:
    """Determine the dashboard group for a worktree/ticket/PR combination.

    Priority order:
    1. Has an open/draft PR → UNDER_REVIEW
    2. Has a ticket in progress and a worktree → CODING_IN_PROGRESS
    3. Has a worktree (with or without ticket) → WORKTREE_CREATED
    4. Has a ticket but no worktree → NOT_STARTED
    """
    if pr is not None and pr.state in {PRState.OPEN, PRState.DRAFT}:
        return TicketWorkflowState.UNDER_REVIEW
    if (
        ticket is not None
        and ticket.status in {TicketStatus.IN_PROGRESS, TicketStatus.IN_REVIEW}
        and worktree is not None
    ):
        return TicketWorkflowState.CODING_IN_PROGRESS
    if worktree is not None:
        return TicketWorkflowState.WORKTREE_CREATED
    if ticket is not None:
        return TicketWorkflowState.NOT_STARTED
    return TicketWorkflowState.WORKTREE_CREATED


def resolve_ticket(worktree: WorktreeInfo, tickets: list[Ticket]) -> Ticket | None:
    """Return the Ticket whose branch_name matches worktree.branch, or None."""
    branch = _normalize_branch(worktree.branch)
    for ticket in tickets:
        if _normalize_branch(ticket.branch_name) == branch:
            return ticket
    return None


def resolve_pr(worktree: WorktreeInfo, prs: list[PullRequest]) -> PullRequest | None:
    """Return the PullRequest whose head_branch matches worktree.branch, or None."""
    branch = _normalize_branch(worktree.branch)
    for pr in prs:
        if _normalize_branch(pr.head_branch) == branch:
            return pr
    return None


@dataclass
class WorktreeMapping:
    """Resolved associations for a single worktree."""

    worktree_path: str
    ticket: Ticket | None
    pr: PullRequest | None


class MappingRegistry:
    """In-memory registry of worktree → ticket/PR mappings.

    Call refresh() whenever the underlying data changes.  All subsequent
    get_ticket() / get_pr() calls are O(1) dict lookups — safe to call on
    every render.
    """

    def __init__(self) -> None:
        self._mappings: dict[str, WorktreeMapping] = {}
        self._unmatched_tickets: list[Ticket] = []

    def refresh(
        self,
        worktrees: list[WorktreeInfo],
        tickets: list[Ticket],
        prs: list[PullRequest],
    ) -> None:
        """Recompute all mappings and replace the previous registry contents."""
        self._mappings = {
            wt.path: WorktreeMapping(
                worktree_path=wt.path,
                ticket=resolve_ticket(wt, tickets),
                pr=resolve_pr(wt, prs),
            )
            for wt in worktrees
        }
        matched_branches = {
            _normalize_branch(m.ticket.branch_name)
            for m in self._mappings.values()
            if m.ticket is not None
        }
        self._unmatched_tickets = [
            t
            for t in tickets
            if _normalize_branch(t.branch_name) not in matched_branches
        ]

    def get_ticket(self, worktree_path: str) -> Ticket | None:
        mapping = self._mappings.get(worktree_path)
        return mapping.ticket if mapping else None

    def get_pr(self, worktree_path: str) -> PullRequest | None:
        mapping = self._mappings.get(worktree_path)
        return mapping.pr if mapping else None

    def get_mapping(self, worktree_path: str) -> WorktreeMapping | None:
        return self._mappings.get(worktree_path)

    def all_mappings(self) -> list[WorktreeMapping]:
        return list(self._mappings.values())

    def get_workflow_state(self, worktree_path: str) -> TicketWorkflowState:
        """Return the workflow state for a worktree based on its ticket/PR."""
        mapping = self._mappings.get(worktree_path)
        if mapping is None:
            return TicketWorkflowState.WORKTREE_CREATED
        return classify_workflow_state(
            WorktreeInfo(path=worktree_path),
            mapping.ticket,
            mapping.pr,
        )

    @property
    def unmatched_tickets(self) -> list[Ticket]:
        """Tickets whose branch_name doesn't match any worktree."""
        return self._unmatched_tickets
