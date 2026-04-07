"""GitHub REST API client using PyGithub."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from types import TracebackType
from typing import TypeVar

from github import (
    Auth,
    BadCredentialsException,
    Github,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.PullRequest import PullRequest as GHPullRequest
from github.Repository import Repository

from modules.core.config import AppConfig
from modules.github.models import Comment, PRState, PullRequest

__all__ = [
    "GitHubAuthError",
    "GitHubClient",
    "GitHubClientError",
    "GitHubNetworkError",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
    "_determine_pr_state",
    "_parse_comment",
    "_parse_pull_request",
]

T = TypeVar("T")


# --- Exceptions ---


class GitHubClientError(Exception):
    """Base exception for GitHub client errors."""


class GitHubAuthError(GitHubClientError):
    """Raised when authentication fails (invalid/missing token)."""


class GitHubNotFoundError(GitHubClientError):
    """Raised when a requested resource does not exist (404)."""


class GitHubRateLimitError(GitHubClientError):
    """Raised when the GitHub API rate limit is exceeded."""


class GitHubNetworkError(GitHubClientError):
    """Raised on transport/connectivity failures."""


# --- Client ---


class GitHubClient:
    """Async-friendly wrapper around PyGithub's synchronous Github client.

    All GitHub API calls are executed via ``asyncio.to_thread()`` to avoid
    blocking the event loop.  Use as an async context manager::

        async with GitHubClient(token="ghp_...", repo_slug="owner/repo") as client:
            ...
    """

    def __init__(self, token: str, repo_slug: str) -> None:
        self._token = token
        self._repo_slug = repo_slug
        self._gh: Github | None = None
        self._repo: Repository | None = None

    @classmethod
    def from_config(cls, config: AppConfig) -> GitHubClient:
        """Create a client from application config.

        Raises ``GitHubAuthError`` if the token is not configured.
        Raises ``GitHubClientError`` if the repo slug is not configured.
        """
        if config.github_token is None:
            raise GitHubAuthError("GitHub token not configured")
        if config.github_repo is None:
            raise GitHubClientError("GitHub repo not configured")
        return cls(token=config.github_token, repo_slug=config.github_repo)

    # -- Lifecycle --

    async def connect(self) -> None:
        """Initialize the PyGithub client and fetch the repository.

        Validates credentials and repo access eagerly so errors
        surface at startup rather than on first query.
        """

        def _connect() -> tuple[Github, Repository]:
            auth = Auth.Token(self._token)
            gh = Github(auth=auth)
            repo = gh.get_repo(self._repo_slug)
            return gh, repo

        try:
            self._gh, self._repo = await asyncio.to_thread(_connect)
        except BadCredentialsException as exc:
            raise GitHubAuthError(str(exc)) from exc
        except UnknownObjectException as exc:
            raise GitHubNotFoundError(
                f"Repository not found: {self._repo_slug}"
            ) from exc
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError(str(exc)) from exc
        except GithubException as exc:
            raise GitHubNetworkError(str(exc)) from exc
        except Exception as exc:
            raise GitHubNetworkError(str(exc)) from exc

    async def close(self) -> None:
        """Close the underlying PyGithub session."""
        if self._gh is not None:
            await asyncio.to_thread(self._gh.close)
            self._gh = None
            self._repo = None

    async def __aenter__(self) -> GitHubClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    # -- Internal helpers --

    def _require_repo(self) -> Repository:
        """Return the cached Repository or raise if not connected."""
        if self._repo is None:
            raise GitHubClientError("Client is not connected. Call connect() first.")
        return self._repo

    async def _run_sync(self, fn: Callable[[], T]) -> T:
        """Run a synchronous callable in a thread, mapping PyGithub exceptions.

        All domain query methods should use this helper to execute
        blocking PyGithub calls off the event loop.
        """
        try:
            return await asyncio.to_thread(fn)
        except BadCredentialsException as exc:
            raise GitHubAuthError(str(exc)) from exc
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError(str(exc)) from exc
        except UnknownObjectException as exc:
            raise GitHubNotFoundError(str(exc)) from exc
        except GithubException as exc:
            raise GitHubNetworkError(str(exc)) from exc
        except Exception as exc:
            raise GitHubNetworkError(str(exc)) from exc

    # -- Domain queries --

    async def fetch_open_prs(self) -> list[PullRequest]:
        """Fetch all open pull requests for the configured repository."""
        repo = self._require_repo()
        pulls = await self._run_sync(lambda: list(repo.get_pulls(state="open")))
        return [_parse_pull_request(pr) for pr in pulls]

    async def fetch_pr_comments(self, pr_number: int) -> list[Comment]:
        """Fetch all comments for a pull request.

        Retrieves both general issue comments and inline review comments,
        merges them, and returns sorted by ``created_at`` (oldest first).
        All comments are initially marked as unread (``is_read=False``).
        """
        repo = self._require_repo()

        def _fetch() -> list[Comment]:
            pr = repo.get_pull(pr_number)
            issue_comments = [_parse_comment(c) for c in pr.get_issue_comments()]
            review_comments = [_parse_comment(c) for c in pr.get_review_comments()]
            merged = issue_comments + review_comments
            merged.sort(key=lambda c: c.created_at)
            return merged

        return await self._run_sync(_fetch)

    async def get_pr_merge_status(self, pr_number: int) -> str:
        """Return the merge status of a pull request.

        Returns one of ``"open"``, ``"merged"``, ``"closed"``, ``"draft"``.

        GitHub computes the ``mergeable`` field asynchronously, so the first
        fetch may return ``None``.  When that happens this method sleeps 1 s
        and re-fetches the PR once before determining the status.
        """
        repo = self._require_repo()

        def _fetch() -> str:
            import time

            pr = repo.get_pull(pr_number)
            if pr.mergeable is None:
                time.sleep(1)
                pr = repo.get_pull(pr_number)
            return _determine_pr_state(pr)

        return await self._run_sync(_fetch)


# --- Response parsing ---


def _parse_comment(comment: object) -> Comment:
    """Convert a PyGithub comment object to a domain Comment.

    Works with both ``IssueComment`` and ``PullRequestComment`` objects
    since they share the same attribute interface.
    """
    user = getattr(comment, "user", None)
    author = user.login if user is not None else "Unknown"
    return Comment(
        id=comment.id,  # type: ignore[union-attr]
        body=comment.body,  # type: ignore[union-attr]
        author=author,
        created_at=comment.created_at,  # type: ignore[union-attr]
        is_read=False,
    )


def _determine_pr_state(pr: GHPullRequest) -> str:
    """Determine the merge status string for a PyGithub PullRequest."""
    if pr.draft:
        return PRState.DRAFT.value
    if pr.merged:
        return PRState.MERGED.value
    if pr.state == "closed":
        return PRState.CLOSED.value
    return PRState.OPEN.value


def _parse_pull_request(pr: GHPullRequest) -> PullRequest:
    """Convert a PyGithub PullRequest to a domain PullRequest."""
    state = PRState(_determine_pr_state(pr))

    return PullRequest(
        number=pr.number,
        title=pr.title,
        state=state,
        url=pr.html_url,
        head_branch=pr.head.ref,
        base_branch=pr.base.ref,
        merged=pr.merged,
        draft=pr.draft,
        updated_at=pr.updated_at,
        unread_comment_count=0,
    )
