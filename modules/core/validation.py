"""Async helpers for validating API credentials."""

from __future__ import annotations

import asyncio

import httpx

from modules.linear.client import (
    LinearAuthError,
    LinearClient,
    LinearNetworkError,
    LinearQueryError,
)

__all__ = [
    "validate_github_token",
    "validate_linear_key",
    "validate_linear_team",
]

_TIMEOUT = 5.0
_GITHUB_USER_URL = "https://api.github.com/user"

_VIEWER_QUERY = "{ viewer { id name } }"
_TEAM_QUERY = "query($id: String!) { team(id: $id) { name } }"


def _is_auth_query_error(exc: LinearQueryError) -> bool:
    """Return True if the GraphQL error represents an authentication failure."""
    msg = str(exc).lower()
    return "authentication" in msg or "not authenticated" in msg


async def validate_linear_key(api_key: str) -> tuple[bool, str]:
    """Test a Linear API key by fetching the authenticated viewer.

    Returns:
        ``(True, "Authenticated as {name}")`` on success, or
        ``(False, error_message)`` on failure.
    """
    client = LinearClient(api_key)
    try:
        data = await asyncio.wait_for(client.execute(_VIEWER_QUERY), timeout=_TIMEOUT)
        name = data["viewer"]["name"]
        return True, f"Authenticated as {name}"
    except LinearAuthError as exc:
        return False, f"Authentication failed: {exc}"
    except LinearQueryError as exc:
        if _is_auth_query_error(exc):
            return False, "Authentication failed"
        return False, f"Query error: {exc}"
    except (TimeoutError, LinearNetworkError) as exc:
        return False, f"Network error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"


async def validate_linear_team(api_key: str, team_id: str) -> tuple[bool, str]:
    """Test that a Linear team ID exists and is accessible with the given key.

    Returns:
        ``(True, "Team: {name}")`` on success, or ``(False, error_message)`` on failure.
    """
    client = LinearClient(api_key)
    try:
        data = await asyncio.wait_for(
            client.execute(_TEAM_QUERY, variables={"id": team_id}),
            timeout=_TIMEOUT,
        )
        team = data.get("team")
        if not team:
            return False, "Team not found"
        return True, f"Team: {team['name']}"
    except LinearAuthError as exc:
        return False, f"Authentication failed: {exc}"
    except LinearQueryError as exc:
        if _is_auth_query_error(exc):
            return False, "Authentication failed"
        return False, f"Query error: {exc}"
    except (TimeoutError, LinearNetworkError) as exc:
        return False, f"Network error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"


async def validate_github_token(token: str) -> tuple[bool, str]:
    """Test a GitHub personal access token by fetching the authenticated user.

    Returns:
        ``(True, "Authenticated as {login}")`` on success, or
        ``(False, error_message)`` on failure.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(_GITHUB_USER_URL, headers=headers)
        if response.status_code == 200:
            login = response.json().get("login", "unknown")
            return True, f"Authenticated as {login}"
        if response.status_code in (401, 403):
            return False, "Authentication failed"
        return False, f"HTTP error: {response.status_code}"
    except httpx.TimeoutException:
        return False, "Request timed out"
    except httpx.NetworkError as exc:
        return False, f"Network error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"
