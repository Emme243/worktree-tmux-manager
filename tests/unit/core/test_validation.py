"""Tests for modules.core.validation — API credential validation helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from modules.core.validation import (
    validate_github_token,
    validate_linear_key,
    validate_linear_team,
)
from modules.linear.client import LinearAuthError, LinearNetworkError, LinearQueryError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_KEY = "lin_test_abc123"
_DUMMY_TEAM = "team_xyz"
_AUTH_QUERY_ERROR = LinearQueryError("Authentication required, not authenticated")


# ---------------------------------------------------------------------------
# validate_linear_key
# ---------------------------------------------------------------------------


class TestValidateLinearKey:
    async def _call(self, key: str = _DUMMY_KEY, execute_result=None, side_effect=None):
        with patch(
            "modules.core.validation.LinearClient.execute",
            new_callable=AsyncMock,
            return_value=execute_result,
            side_effect=side_effect,
        ):
            return await validate_linear_key(key)

    @pytest.mark.asyncio
    async def test_success_returns_true_with_name(self):
        result = await self._call(
            execute_result={"viewer": {"id": "u1", "name": "Alice"}}
        )
        assert result == (True, "Authenticated as Alice")

    @pytest.mark.asyncio
    async def test_auth_error_returns_false(self):
        result = await self._call(side_effect=LinearAuthError("bad token"))
        ok, msg = result
        assert ok is False
        assert "Authentication failed" in msg

    @pytest.mark.asyncio
    async def test_query_auth_error_returns_false(self):
        result = await self._call(side_effect=_AUTH_QUERY_ERROR)
        ok, msg = result
        assert ok is False
        assert "Authentication failed" in msg

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self):
        result = await self._call(side_effect=LinearNetworkError("connection refused"))
        ok, msg = result
        assert ok is False
        assert "Network error" in msg

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self):

        result = await self._call(side_effect=TimeoutError())
        ok, msg = result
        assert ok is False
        assert "Network error" in msg


# ---------------------------------------------------------------------------
# validate_linear_team
# ---------------------------------------------------------------------------


class TestValidateLinearTeam:
    async def _call(
        self, key=_DUMMY_KEY, team=_DUMMY_TEAM, execute_result=None, side_effect=None
    ):
        with patch(
            "modules.core.validation.LinearClient.execute",
            new_callable=AsyncMock,
            return_value=execute_result,
            side_effect=side_effect,
        ):
            return await validate_linear_team(key, team)

    @pytest.mark.asyncio
    async def test_success_returns_true_with_team_name(self):
        result = await self._call(execute_result={"team": {"name": "Backend"}})
        assert result == (True, "Team: Backend")

    @pytest.mark.asyncio
    async def test_team_not_found_returns_false(self):
        result = await self._call(execute_result={"team": None})
        assert result == (False, "Team not found")

    @pytest.mark.asyncio
    async def test_auth_error_returns_false(self):
        result = await self._call(side_effect=LinearAuthError("invalid key"))
        ok, msg = result
        assert ok is False
        assert "Authentication failed" in msg

    @pytest.mark.asyncio
    async def test_query_auth_error_returns_false(self):
        result = await self._call(side_effect=_AUTH_QUERY_ERROR)
        ok, msg = result
        assert ok is False
        assert "Authentication failed" in msg

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self):
        result = await self._call(side_effect=LinearNetworkError("timeout"))
        ok, msg = result
        assert ok is False
        assert "Network error" in msg


# ---------------------------------------------------------------------------
# validate_github_token
# ---------------------------------------------------------------------------


class TestValidateGithubToken:
    def _mock_response(
        self, status_code: int, json_data: dict | None = None
    ) -> MagicMock:
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        return response

    @pytest.mark.asyncio
    async def test_success_returns_true_with_login(self):
        mock_response = self._mock_response(200, {"login": "octocat"})
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await validate_github_token("ghp_test")
        assert result == (True, "Authenticated as octocat")

    @pytest.mark.asyncio
    async def test_401_returns_false(self):
        mock_response = self._mock_response(401)
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await validate_github_token("bad_token")
        assert result == (False, "Authentication failed")

    @pytest.mark.asyncio
    async def test_403_returns_false(self):
        mock_response = self._mock_response(403)
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await validate_github_token("bad_token")
        assert result == (False, "Authentication failed")

    @pytest.mark.asyncio
    async def test_other_http_error_returns_status_code(self):
        mock_response = self._mock_response(500)
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await validate_github_token("ghp_test")
        ok, msg = result
        assert ok is False
        assert "500" in msg

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self):
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            result = await validate_github_token("ghp_test")
        assert result == (False, "Request timed out")

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self):
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.NetworkError("unreachable"),
        ):
            result = await validate_github_token("ghp_test")
        ok, msg = result
        assert ok is False
        assert "Network error" in msg
