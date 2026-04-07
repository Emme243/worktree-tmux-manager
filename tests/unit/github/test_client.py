"""Tests for modules.github.client — GitHubClient and exception hierarchy."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from github import (
    BadCredentialsException,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)

from modules.core.config import AppConfig
from modules.github.client import (
    GitHubAuthError,
    GitHubClient,
    GitHubClientError,
    GitHubNetworkError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    _determine_pr_state,
    _parse_comment,
    _parse_pull_request,
)
from modules.github.models import Comment, PRState, PullRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_TOKEN = "ghp_test_token_abc123"
_DUMMY_SLUG = "owner/repo"


def _make_config(
    token: str | None = _DUMMY_TOKEN,
    repo: str | None = _DUMMY_SLUG,
) -> AppConfig:
    return AppConfig(
        repo_path=Path("/tmp/fake"),
        github_token=token,
        github_repo=repo,
    )


def _make_github_exc(cls, status=400, message="error"):
    """Create a PyGithub exception with required positional args."""
    return cls(status, {"message": message}, None, message)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_base_is_exception(self):
        assert issubclass(GitHubClientError, Exception)

    def test_auth_error_is_client_error(self):
        assert issubclass(GitHubAuthError, GitHubClientError)

    def test_not_found_error_is_client_error(self):
        assert issubclass(GitHubNotFoundError, GitHubClientError)

    def test_rate_limit_error_is_client_error(self):
        assert issubclass(GitHubRateLimitError, GitHubClientError)

    def test_network_error_is_client_error(self):
        assert issubclass(GitHubNetworkError, GitHubClientError)

    def test_all_catchable_as_base(self):
        for cls in (
            GitHubAuthError,
            GitHubNotFoundError,
            GitHubRateLimitError,
            GitHubNetworkError,
        ):
            with pytest.raises(GitHubClientError):
                raise cls("test")


# ---------------------------------------------------------------------------
# GitHubClient.__init__
# ---------------------------------------------------------------------------


class TestGitHubClientInit:
    def test_stores_token(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        assert client._token == _DUMMY_TOKEN

    def test_stores_repo_slug(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        assert client._repo_slug == _DUMMY_SLUG

    def test_gh_is_none_initially(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        assert client._gh is None

    def test_repo_is_none_initially(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        assert client._repo is None


# ---------------------------------------------------------------------------
# GitHubClient.from_config
# ---------------------------------------------------------------------------


class TestGitHubClientFromConfig:
    def test_creates_client_with_valid_config(self):
        config = _make_config()
        client = GitHubClient.from_config(config)
        assert isinstance(client, GitHubClient)
        assert client._token == _DUMMY_TOKEN
        assert client._repo_slug == _DUMMY_SLUG

    def test_raises_auth_error_when_token_is_none(self):
        config = _make_config(token=None)
        with pytest.raises(GitHubAuthError, match="not configured"):
            GitHubClient.from_config(config)

    def test_raises_client_error_when_repo_is_none(self):
        config = _make_config(repo=None)
        with pytest.raises(GitHubClientError, match="not configured"):
            GitHubClient.from_config(config)


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestGitHubClientContextManager:
    async def test_aenter_returns_self(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_repo = MagicMock()
        mock_gh.get_repo.return_value = mock_repo

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            result = await client.__aenter__()
            assert result is client

    async def test_connect_initializes_gh_and_repo(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_repo = MagicMock()
        mock_gh.get_repo.return_value = mock_repo

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            await client.connect()
            assert client._gh is mock_gh
            assert client._repo is mock_repo

    async def test_close_clears_state(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_repo = MagicMock()
        mock_gh.get_repo.return_value = mock_repo

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            async with client:
                assert client._gh is not None
                assert client._repo is not None
            assert client._gh is None
            assert client._repo is None

    async def test_close_called_on_exception(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_repo = MagicMock()
        mock_gh.get_repo.return_value = mock_repo

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            with pytest.raises(RuntimeError):
                async with client:
                    raise RuntimeError("boom")
            mock_gh.close.assert_called_once()
            assert client._gh is None


# ---------------------------------------------------------------------------
# connect — exception mapping
# ---------------------------------------------------------------------------


class TestGitHubClientConnect:
    async def test_bad_credentials_raises_auth_error(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = _make_github_exc(
            BadCredentialsException, 401, "Bad credentials"
        )

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            with pytest.raises(GitHubAuthError):
                await client.connect()

    async def test_unknown_object_raises_not_found_error(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = _make_github_exc(
            UnknownObjectException, 404, "Not Found"
        )

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            with pytest.raises(GitHubNotFoundError, match="Repository not found"):
                await client.connect()

    async def test_rate_limit_raises_rate_limit_error(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = _make_github_exc(
            RateLimitExceededException, 403, "Rate limit"
        )

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            with pytest.raises(GitHubRateLimitError):
                await client.connect()

    async def test_generic_github_exception_raises_network_error(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = _make_github_exc(
            GithubException, 500, "Server error"
        )

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            with pytest.raises(GitHubNetworkError):
                await client.connect()

    async def test_generic_exception_raises_network_error(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = ConnectionError("DNS failure")

        with (
            patch("modules.github.client.Auth.Token"),
            patch("modules.github.client.Github", return_value=mock_gh),
        ):
            with pytest.raises(GitHubNetworkError, match="DNS failure"):
                await client.connect()


# ---------------------------------------------------------------------------
# _run_sync — exception mapping
# ---------------------------------------------------------------------------


class TestRunSync:
    @pytest.fixture()
    def connected_client(self):
        """Return a GitHubClient with _repo set (without actual connect)."""
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        client._gh = MagicMock()
        client._repo = MagicMock()
        return client

    async def test_returns_result(self, connected_client):
        result = await connected_client._run_sync(lambda: 42)
        assert result == 42

    async def test_bad_credentials_mapped(self, connected_client):
        def _raise():
            raise _make_github_exc(BadCredentialsException, 401)

        with pytest.raises(GitHubAuthError):
            await connected_client._run_sync(_raise)

    async def test_rate_limit_mapped(self, connected_client):
        def _raise():
            raise _make_github_exc(RateLimitExceededException, 403)

        with pytest.raises(GitHubRateLimitError):
            await connected_client._run_sync(_raise)

    async def test_unknown_object_mapped(self, connected_client):
        def _raise():
            raise _make_github_exc(UnknownObjectException, 404)

        with pytest.raises(GitHubNotFoundError):
            await connected_client._run_sync(_raise)

    async def test_generic_github_exception_mapped(self, connected_client):
        def _raise():
            raise _make_github_exc(GithubException, 500)

        with pytest.raises(GitHubNetworkError):
            await connected_client._run_sync(_raise)

    async def test_generic_exception_mapped(self, connected_client):
        def _raise():
            raise ConnectionError("timeout")

        with pytest.raises(GitHubNetworkError, match="timeout"):
            await connected_client._run_sync(_raise)


# ---------------------------------------------------------------------------
# _require_repo
# ---------------------------------------------------------------------------


class TestRequireRepo:
    def test_raises_when_not_connected(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        with pytest.raises(GitHubClientError, match="not connected"):
            client._require_repo()

    def test_returns_repo_when_connected(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        mock_repo = MagicMock()
        client._repo = mock_repo
        assert client._require_repo() is mock_repo


# ---------------------------------------------------------------------------
# _parse_pull_request
# ---------------------------------------------------------------------------

_SAMPLE_UPDATED_AT = datetime(2025, 1, 15, 12, 0, 0)


def _make_mock_pr(**overrides):
    """Create a MagicMock mimicking a PyGithub PullRequest."""
    pr = MagicMock()
    pr.number = overrides.get("number", 42)
    pr.title = overrides.get("title", "Fix the thing")
    pr.state = overrides.get("state", "open")
    pr.html_url = overrides.get("html_url", "https://github.com/owner/repo/pull/42")
    pr.head.ref = overrides.get("head_ref", "feature-branch")
    pr.base.ref = overrides.get("base_ref", "main")
    pr.merged = overrides.get("merged", False)
    pr.draft = overrides.get("draft", False)
    pr.updated_at = overrides.get("updated_at", _SAMPLE_UPDATED_AT)
    return pr


class TestParsePullRequest:
    def test_parses_open_pr(self):
        pr = _make_mock_pr()
        result = _parse_pull_request(pr)
        assert isinstance(result, PullRequest)
        assert result.number == 42
        assert result.title == "Fix the thing"
        assert result.state == PRState.OPEN
        assert result.url == "https://github.com/owner/repo/pull/42"
        assert result.head_branch == "feature-branch"
        assert result.base_branch == "main"
        assert result.merged is False
        assert result.draft is False
        assert result.updated_at == _SAMPLE_UPDATED_AT

    def test_draft_pr_has_draft_state(self):
        pr = _make_mock_pr(state="open", draft=True)
        result = _parse_pull_request(pr)
        assert result.state == PRState.DRAFT

    def test_merged_pr_has_merged_state(self):
        pr = _make_mock_pr(state="closed", merged=True)
        result = _parse_pull_request(pr)
        assert result.state == PRState.MERGED

    def test_closed_pr_has_closed_state(self):
        pr = _make_mock_pr(state="closed", merged=False)
        result = _parse_pull_request(pr)
        assert result.state == PRState.CLOSED

    def test_unread_comment_count_is_zero(self):
        pr = _make_mock_pr()
        result = _parse_pull_request(pr)
        assert result.unread_comment_count == 0


# ---------------------------------------------------------------------------
# fetch_open_prs
# ---------------------------------------------------------------------------


class TestFetchOpenPRs:
    @pytest.fixture()
    def connected_client(self):
        """Return a GitHubClient with _repo set (without actual connect)."""
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        client._gh = MagicMock()
        client._repo = MagicMock()
        return client

    async def test_returns_domain_pull_requests(self, connected_client):
        mock_pr = _make_mock_pr()
        connected_client._repo.get_pulls.return_value = [mock_pr]
        result = await connected_client.fetch_open_prs()
        assert len(result) == 1
        assert isinstance(result[0], PullRequest)
        assert result[0].number == 42

    async def test_empty_response(self, connected_client):
        connected_client._repo.get_pulls.return_value = []
        result = await connected_client.fetch_open_prs()
        assert result == []

    async def test_multiple_prs(self, connected_client):
        pr1 = _make_mock_pr(number=1, title="First")
        pr2 = _make_mock_pr(number=2, title="Second")
        connected_client._repo.get_pulls.return_value = [pr1, pr2]
        result = await connected_client.fetch_open_prs()
        assert len(result) == 2
        assert result[0].number == 1
        assert result[1].number == 2

    async def test_calls_get_pulls_with_state_open(self, connected_client):
        connected_client._repo.get_pulls.return_value = []
        await connected_client.fetch_open_prs()
        connected_client._repo.get_pulls.assert_called_once_with(state="open")

    async def test_raises_when_not_connected(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        with pytest.raises(GitHubClientError, match="not connected"):
            await client.fetch_open_prs()

    async def test_propagates_rate_limit_error(self, connected_client):
        connected_client._repo.get_pulls.side_effect = _make_github_exc(
            RateLimitExceededException, 403, "Rate limit"
        )
        with pytest.raises(GitHubRateLimitError):
            await connected_client.fetch_open_prs()


# ---------------------------------------------------------------------------
# _parse_comment
# ---------------------------------------------------------------------------

_SAMPLE_CREATED_AT = datetime(2025, 3, 10, 8, 0, 0)


def _make_mock_comment(**overrides):
    """Create a MagicMock mimicking a PyGithub IssueComment or PullRequestComment."""
    comment = MagicMock()
    comment.id = overrides.get("id", 101)
    comment.body = overrides.get("body", "Looks good!")
    comment.created_at = overrides.get("created_at", _SAMPLE_CREATED_AT)
    user = overrides.get("user", MagicMock())
    if user is not None:
        user.login = overrides.get("login", "octocat")
    comment.user = user
    return comment


class TestParseComment:
    def test_parses_all_fields(self):
        comment = _make_mock_comment()
        result = _parse_comment(comment)
        assert isinstance(result, Comment)
        assert result.id == 101
        assert result.body == "Looks good!"
        assert result.author == "octocat"
        assert result.created_at == _SAMPLE_CREATED_AT
        assert result.is_read is False

    def test_missing_user_returns_unknown(self):
        comment = _make_mock_comment(user=None)
        result = _parse_comment(comment)
        assert result.author == "Unknown"

    def test_custom_values(self):
        ts = datetime(2025, 6, 1, 12, 30, 0)
        comment = _make_mock_comment(
            id=999, body="LGTM", login="reviewer", created_at=ts
        )
        result = _parse_comment(comment)
        assert result.id == 999
        assert result.body == "LGTM"
        assert result.author == "reviewer"
        assert result.created_at == ts


# ---------------------------------------------------------------------------
# fetch_pr_comments
# ---------------------------------------------------------------------------


class TestFetchPRComments:
    @pytest.fixture()
    def connected_client(self):
        """Return a GitHubClient with _repo set (without actual connect)."""
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        client._gh = MagicMock()
        client._repo = MagicMock()
        return client

    async def test_returns_empty_list_when_no_comments(self, connected_client):
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_review_comments.return_value = []
        connected_client._repo.get_pull.return_value = mock_pr
        result = await connected_client.fetch_pr_comments(42)
        assert result == []

    async def test_merges_and_sorts_by_created_at(self, connected_client):
        t1 = datetime(2025, 1, 1, 10, 0, 0)
        t2 = datetime(2025, 1, 1, 11, 0, 0)
        t3 = datetime(2025, 1, 1, 12, 0, 0)

        issue_comment = _make_mock_comment(id=1, body="issue", created_at=t3)
        review_comment1 = _make_mock_comment(id=2, body="review1", created_at=t1)
        review_comment2 = _make_mock_comment(id=3, body="review2", created_at=t2)

        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [issue_comment]
        mock_pr.get_review_comments.return_value = [review_comment1, review_comment2]
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.fetch_pr_comments(42)
        assert len(result) == 3
        assert result[0].id == 2  # t1 — earliest
        assert result[1].id == 3  # t2
        assert result[2].id == 1  # t3 — latest

    async def test_all_comments_are_unread(self, connected_client):
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [_make_mock_comment()]
        mock_pr.get_review_comments.return_value = [_make_mock_comment(id=200)]
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.fetch_pr_comments(1)
        assert all(c.is_read is False for c in result)

    async def test_calls_get_pull_with_pr_number(self, connected_client):
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_review_comments.return_value = []
        connected_client._repo.get_pull.return_value = mock_pr

        await connected_client.fetch_pr_comments(99)
        connected_client._repo.get_pull.assert_called_once_with(99)

    async def test_raises_when_not_connected(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        with pytest.raises(GitHubClientError, match="not connected"):
            await client.fetch_pr_comments(1)

    async def test_propagates_not_found_error(self, connected_client):
        connected_client._repo.get_pull.side_effect = _make_github_exc(
            UnknownObjectException, 404, "Not Found"
        )
        with pytest.raises(GitHubNotFoundError):
            await connected_client.fetch_pr_comments(999)


# ---------------------------------------------------------------------------
# _determine_pr_state
# ---------------------------------------------------------------------------


class TestDeterminePRState:
    def test_draft_pr(self):
        pr = _make_mock_pr(state="open", draft=True)
        assert _determine_pr_state(pr) == "draft"

    def test_merged_pr(self):
        pr = _make_mock_pr(state="closed", merged=True)
        assert _determine_pr_state(pr) == "merged"

    def test_closed_pr(self):
        pr = _make_mock_pr(state="closed", merged=False)
        assert _determine_pr_state(pr) == "closed"

    def test_open_pr(self):
        pr = _make_mock_pr(state="open", draft=False, merged=False)
        assert _determine_pr_state(pr) == "open"

    def test_draft_takes_priority_over_merged(self):
        pr = _make_mock_pr(state="closed", draft=True, merged=True)
        assert _determine_pr_state(pr) == "draft"


# ---------------------------------------------------------------------------
# get_pr_merge_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetPRMergeStatus:
    @pytest.fixture
    def connected_client(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        client._gh = MagicMock()
        client._repo = MagicMock()
        return client

    async def test_returns_open(self, connected_client):
        mock_pr = _make_mock_pr(state="open", draft=False, merged=False)
        mock_pr.mergeable = True
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.get_pr_merge_status(42)
        assert result == "open"

    async def test_returns_merged(self, connected_client):
        mock_pr = _make_mock_pr(state="closed", merged=True)
        mock_pr.mergeable = False
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.get_pr_merge_status(42)
        assert result == "merged"

    async def test_returns_closed(self, connected_client):
        mock_pr = _make_mock_pr(state="closed", merged=False)
        mock_pr.mergeable = False
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.get_pr_merge_status(42)
        assert result == "closed"

    async def test_returns_draft(self, connected_client):
        mock_pr = _make_mock_pr(state="open", draft=True)
        mock_pr.mergeable = True
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.get_pr_merge_status(42)
        assert result == "draft"

    async def test_retries_on_null_mergeable(self, connected_client):
        first_pr = _make_mock_pr(state="open")
        first_pr.mergeable = None
        second_pr = _make_mock_pr(state="open")
        second_pr.mergeable = True
        connected_client._repo.get_pull.side_effect = [first_pr, second_pr]

        with patch("time.sleep") as mock_sleep:
            result = await connected_client.get_pr_merge_status(42)

        assert result == "open"
        mock_sleep.assert_called_once_with(1)
        assert connected_client._repo.get_pull.call_count == 2

    async def test_returns_status_even_if_mergeable_still_none_after_retry(
        self, connected_client
    ):
        mock_pr = _make_mock_pr(state="open")
        mock_pr.mergeable = None
        connected_client._repo.get_pull.return_value = mock_pr

        with patch("time.sleep"):
            result = await connected_client.get_pr_merge_status(42)

        assert result == "open"
        assert connected_client._repo.get_pull.call_count == 2

    async def test_no_retry_when_mergeable_is_set(self, connected_client):
        mock_pr = _make_mock_pr(state="open")
        mock_pr.mergeable = True
        connected_client._repo.get_pull.return_value = mock_pr

        result = await connected_client.get_pr_merge_status(42)

        assert result == "open"
        connected_client._repo.get_pull.assert_called_once_with(42)

    async def test_raises_when_not_connected(self):
        client = GitHubClient(token=_DUMMY_TOKEN, repo_slug=_DUMMY_SLUG)
        with pytest.raises(GitHubClientError, match="not connected"):
            await client.get_pr_merge_status(1)

    async def test_propagates_not_found_error(self, connected_client):
        connected_client._repo.get_pull.side_effect = _make_github_exc(
            UnknownObjectException, 404, "Not Found"
        )
        with pytest.raises(GitHubNotFoundError):
            await connected_client.get_pr_merge_status(999)
