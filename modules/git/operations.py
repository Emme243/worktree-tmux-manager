"""Async git command operations for worktree management."""

from __future__ import annotations

import asyncio

from .models import GitError, WorkingTreeStatus, WorktreeInfo


async def run_git(repo_dir: str, *args: str) -> str:
    """Run ``git -C <repo_dir> <args>`` and return stdout.

    Raises GitError on failure.
    """
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        repo_dir,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise GitError(stderr.decode().strip() or "Unknown git error")
    return stdout.decode()


async def is_git_repo(path: str) -> bool:
    try:
        await run_git(path, "rev-parse", "--git-dir")
        return True
    except GitError:
        return False


def parse_worktree_porcelain(output: str) -> list[WorktreeInfo]:
    """Parse ``git worktree list --porcelain`` output."""
    entries: list[WorktreeInfo] = []
    blocks = output.strip().split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        wt = WorktreeInfo()
        for line in block.strip().splitlines():
            if line.startswith("worktree "):
                wt.path = line[len("worktree ") :]
            elif line.startswith("HEAD "):
                wt.head = line[len("HEAD ") :][:8]
            elif line.startswith("branch "):
                wt.branch = line[len("branch ") :].removeprefix("refs/heads/")
            elif line == "bare":
                wt.is_bare = True
                wt.branch = "(bare)"
            elif line == "detached":
                wt.is_detached = True
                wt.branch = "(detached)"
            elif line.startswith("locked"):
                wt.locked = True
                rest = line[len("locked") :].strip()
                if rest:
                    wt.lock_reason = rest
            elif line.startswith("prunable"):
                wt.prunable = True
        entries.append(wt)
    return entries


async def list_worktrees(repo_dir: str) -> list[WorktreeInfo]:
    output = await run_git(repo_dir, "worktree", "list", "--porcelain")
    return parse_worktree_porcelain(output)


def parse_status_porcelain(output: str) -> WorkingTreeStatus:
    """Parse ``git status --porcelain=v1`` output into file-change counts."""
    status = WorkingTreeStatus()
    for line in output.splitlines():
        if len(line) < 2:
            continue
        x, y = line[0], line[1]
        if x == "?" and y == "?":
            status.untracked += 1
        elif x == "!" and y == "!":
            continue
        elif x == "U" or y == "U" or (x == "A" and y == "A") or (x == "D" and y == "D"):
            status.conflicted += 1
        else:
            if x in "MADRC":
                status.staged += 1
            if y in "MD":
                status.modified += 1
    return status


async def get_worktree_status(wt_path: str) -> WorkingTreeStatus:
    """Get working directory status counts for a single worktree."""
    output = await run_git(wt_path, "status", "--porcelain=v1")
    return parse_status_porcelain(output)


async def populate_worktree_statuses(worktrees: list[WorktreeInfo]) -> None:
    """Fetch working tree status for all non-bare worktrees concurrently."""

    async def _fetch(wt: WorktreeInfo) -> None:
        if wt.is_bare:
            return
        try:
            wt.wt_status = await get_worktree_status(wt.path)
        except GitError:
            wt.wt_status = None

    await asyncio.gather(*[_fetch(wt) for wt in worktrees])


async def list_branches(repo_dir: str) -> list[str]:
    output = await run_git(repo_dir, "branch", "-a", "--format=%(refname:short)")
    return [b.strip() for b in output.strip().splitlines() if b.strip()]


async def add_worktree(
    repo_dir: str,
    wt_path: str,
    branch: str | None = None,
    new_branch: str | None = None,
    detached: bool = False,
) -> str:
    args = ["worktree", "add"]
    if new_branch:
        args += ["-b", new_branch]
    if detached:
        args.append("--detach")
    args.append(wt_path)
    if branch:
        args.append(branch)
    return await run_git(repo_dir, *args)


async def remove_worktree(repo_dir: str, wt_path: str, force: bool = False) -> str:
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(wt_path)
    return await run_git(repo_dir, *args)


async def move_worktree(repo_dir: str, wt_path: str, new_path: str) -> str:
    return await run_git(repo_dir, "worktree", "move", wt_path, new_path)


async def lock_worktree(repo_dir: str, wt_path: str, reason: str = "") -> str:
    args = ["worktree", "lock"]
    if reason:
        args += ["--reason", reason]
    args.append(wt_path)
    return await run_git(repo_dir, *args)


async def unlock_worktree(repo_dir: str, wt_path: str) -> str:
    return await run_git(repo_dir, "worktree", "unlock", wt_path)


async def prune_worktrees(repo_dir: str) -> str:
    return await run_git(repo_dir, "worktree", "prune", "--verbose")


async def repair_worktrees(repo_dir: str) -> str:
    return await run_git(repo_dir, "worktree", "repair")
