"""Branch ↔ Ticket and Worktree ↔ PR mapping utilities."""

from __future__ import annotations

from dataclasses import dataclass

from modules.git.models import WorktreeInfo
from modules.github.models import PullRequest
from modules.linear.models import Ticket


def _normalize_branch(branch: str) -> str:
    """Strip refs/heads/ prefix for consistent branch name comparison."""
    return branch.removeprefix("refs/heads/")


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
