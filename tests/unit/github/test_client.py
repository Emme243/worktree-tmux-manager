"""Tests for modules.github.client — GitHubClient and exception hierarchy."""

from __future__ import annotations

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
)

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
