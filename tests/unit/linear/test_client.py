"""Tests for modules.linear.client — LinearClient and exception hierarchy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from gql.transport.exceptions import TransportQueryError, TransportServerError

from modules.core.config import AppConfig
from modules.linear.client import (
    LINEAR_API_URL,
    LinearAuthError,
    LinearClient,
    LinearClientError,
    LinearNetworkError,
    LinearQueryError,
    _extract_status_code,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_KEY = "lin_test_api_key_abc123"


def _make_config(api_key: str | None = _DUMMY_KEY) -> AppConfig:
    return AppConfig(repo_path=Path("/tmp/fake"), linear_api_key=api_key)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_base_is_exception(self):
        assert issubclass(LinearClientError, Exception)

    def test_auth_error_is_client_error(self):
        assert issubclass(LinearAuthError, LinearClientError)

    def test_network_error_is_client_error(self):
        assert issubclass(LinearNetworkError, LinearClientError)

    def test_query_error_is_client_error(self):
        assert issubclass(LinearQueryError, LinearClientError)

    def test_query_error_stores_errors_list(self):
        errors = [{"message": "field not found"}]
        exc = LinearQueryError("bad query", errors=errors)
        assert exc.errors == errors

    def test_query_error_defaults_empty_errors(self):
        exc = LinearQueryError("bad query")
        assert exc.errors == []


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_api_url(self):
        assert LINEAR_API_URL == "https://api.linear.app/graphql"


# ---------------------------------------------------------------------------
# LinearClient.__init__
# ---------------------------------------------------------------------------


class TestLinearClientInit:
    def test_stores_api_key(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        assert client._api_key == _DUMMY_KEY

    def test_session_is_none_initially(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        assert client._session is None

    def test_transport_has_correct_url(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        assert client._transport.url == LINEAR_API_URL

    def test_fetch_schema_disabled(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        assert client._client.fetch_schema_from_transport is False


# ---------------------------------------------------------------------------
# LinearClient.from_config
# ---------------------------------------------------------------------------


class TestLinearClientFromConfig:
    def test_creates_client_with_valid_key(self):
        config = _make_config(api_key="lin_valid")
        client = LinearClient.from_config(config)
        assert isinstance(client, LinearClient)
        assert client._api_key == "lin_valid"

    def test_raises_auth_error_when_key_is_none(self):
        config = _make_config(api_key=None)
        with pytest.raises(LinearAuthError, match="not configured"):
            LinearClient.from_config(config)


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestLinearClientContextManager:
    async def test_aenter_returns_self(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        with patch.object(
            client._client, "connect_async", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = AsyncMock()
            result = await client.__aenter__()
            assert result is client

    async def test_connect_and_close_called(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        mock_session = AsyncMock()
        with (
            patch.object(
                client._client, "connect_async", new_callable=AsyncMock
            ) as mock_connect,
            patch.object(
                client._client, "close_async", new_callable=AsyncMock
            ) as mock_close,
        ):
            mock_connect.return_value = mock_session
            async with client:
                assert client._session is mock_session
            mock_connect.assert_awaited_once()
            mock_close.assert_awaited_once()

    async def test_close_called_on_exception(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        with (
            patch.object(client._client, "connect_async", new_callable=AsyncMock),
            patch.object(
                client._client, "close_async", new_callable=AsyncMock
            ) as mock_close,
        ):
            with pytest.raises(RuntimeError):
                async with client:
                    raise RuntimeError("boom")
            mock_close.assert_awaited_once()

    async def test_session_cleared_after_close(self):
        client = LinearClient(api_key=_DUMMY_KEY)
        with (
            patch.object(client._client, "connect_async", new_callable=AsyncMock),
            patch.object(client._client, "close_async", new_callable=AsyncMock),
        ):
            async with client:
                pass
            assert client._session is None


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------


class TestLinearClientExecute:
    @pytest.fixture()
    async def connected(self):
        """Yield (client, mock_session) with a connected LinearClient."""
        client = LinearClient(api_key=_DUMMY_KEY)
        mock_session = AsyncMock()
        with (
            patch.object(
                client._client, "connect_async", new_callable=AsyncMock
            ) as mock_connect,
            patch.object(client._client, "close_async", new_callable=AsyncMock),
        ):
            mock_connect.return_value = mock_session
            async with client:
                yield client, mock_session

    async def test_returns_response_data(self, connected):
        client, mock_session = connected
        expected = {"viewer": {"id": "user_1"}}
        mock_session.execute.return_value = expected

        result = await client.execute("{ viewer { id } }")
        assert result == expected

    async def test_passes_variables(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = {"issue": {"id": "1"}}
        variables = {"id": "issue_1"}

        await client.execute(
            "query($id: String!) { issue(id: $id) { id } }",
            variables=variables,
        )
        _, kwargs = mock_session.execute.call_args
        assert kwargs["variable_values"] == variables

    async def test_server_error_401_raises_auth_error(self, connected):
        client, mock_session = connected
        exc = TransportServerError("401 Unauthorized")
        exc.code = 401
        mock_session.execute.side_effect = exc

        with pytest.raises(LinearAuthError):
            await client.execute("{ viewer { id } }")

    async def test_server_error_403_raises_auth_error(self, connected):
        client, mock_session = connected
        exc = TransportServerError("403 Forbidden")
        exc.code = 403
        mock_session.execute.side_effect = exc

        with pytest.raises(LinearAuthError):
            await client.execute("{ viewer { id } }")

    async def test_server_error_500_raises_network_error(self, connected):
        client, mock_session = connected
        exc = TransportServerError("500 Internal Server Error")
        exc.code = 500
        mock_session.execute.side_effect = exc

        with pytest.raises(LinearNetworkError):
            await client.execute("{ viewer { id } }")

    async def test_query_error_raises_query_error(self, connected):
        client, mock_session = connected
        exc = TransportQueryError("field not found")
        exc.errors = [{"message": "field not found"}]
        mock_session.execute.side_effect = exc

        with pytest.raises(LinearQueryError) as exc_info:
            await client.execute("{ bad { query } }")
        assert exc_info.value.errors == [{"message": "field not found"}]

    async def test_generic_exception_raises_network_error(self, connected):
        client, mock_session = connected
        mock_session.execute.side_effect = ConnectionError("DNS failure")

        with pytest.raises(LinearNetworkError, match="DNS failure"):
            await client.execute("{ viewer { id } }")

    async def test_sessionless_fallback(self):
        """When not connected, execute falls back to execute_async."""
        client = LinearClient(api_key=_DUMMY_KEY)
        assert client._session is None
        expected = {"viewer": {"id": "u1"}}

        with patch.object(
            client._client, "execute_async", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = expected
            result = await client.execute("{ viewer { id } }")
            assert result == expected
            mock_exec.assert_awaited_once()


# ---------------------------------------------------------------------------
# _extract_status_code
# ---------------------------------------------------------------------------


class TestExtractStatusCode:
    def test_extracts_from_code_attribute(self):
        exc = TransportServerError("error")
        exc.code = 401
        assert _extract_status_code(exc) == 401

    def test_extracts_from_string_representation(self):
        exc = TransportServerError("401 Unauthorized")
        assert _extract_status_code(exc) == 401

    def test_returns_none_when_no_code(self):
        exc = TransportServerError("something went wrong")
        assert _extract_status_code(exc) is None
