"""Git operations and data models."""

from .models import GitError, WorkingTreeStatus, WorktreeInfo
from .operations import (
    add_worktree,
    is_git_repo,
    list_branches,
    list_worktrees,
    lock_worktree,
    move_worktree,
    populate_worktree_statuses,
    prune_worktrees,
    remove_worktree,
    repair_worktrees,
    unlock_worktree,
)

__all__ = [
    "GitError",
    "WorkingTreeStatus",
    "WorktreeInfo",
    "add_worktree",
    "is_git_repo",
    "list_branches",
    "list_worktrees",
    "lock_worktree",
    "move_worktree",
    "populate_worktree_statuses",
    "prune_worktrees",
    "remove_worktree",
    "repair_worktrees",
    "unlock_worktree",
]
