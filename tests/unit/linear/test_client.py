"""Tests for modules.linear.client — LinearClient and exception hierarchy."""

from __future__ import annotations

from datetime import UTC
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
    _map_state_type,
    _parse_comment,
    _parse_ticket,
)
from modules.linear.models import Comment, Ticket, TicketStatus

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


# ---------------------------------------------------------------------------
# _map_state_type
# ---------------------------------------------------------------------------


class TestMapStateType:
    def test_triage_maps_to_not_started(self):
        assert _map_state_type("triage", "Triage") == TicketStatus.NOT_STARTED

    def test_backlog_maps_to_not_started(self):
        assert _map_state_type("backlog", "Backlog") == TicketStatus.NOT_STARTED

    def test_unstarted_maps_to_not_started(self):
        assert _map_state_type("unstarted", "Todo") == TicketStatus.NOT_STARTED

    def test_started_maps_to_in_progress(self):
        assert _map_state_type("started", "In Progress") == TicketStatus.IN_PROGRESS

    def test_started_with_review_name_maps_to_in_review(self):
        assert _map_state_type("started", "In Review") == TicketStatus.IN_REVIEW

    def test_started_with_review_name_case_insensitive(self):
        assert _map_state_type("started", "code review") == TicketStatus.IN_REVIEW

    def test_unknown_type_defaults_to_not_started(self):
        assert _map_state_type("unknown", "Something") == TicketStatus.NOT_STARTED


# ---------------------------------------------------------------------------
# _parse_ticket
# ---------------------------------------------------------------------------

_SAMPLE_NODE = {
    "id": "issue_1",
    "identifier": "ENG-42",
    "title": "Fix the bug",
    "state": {"name": "In Progress", "type": "started"},
    "branchName": "eng-42-fix-the-bug",
    "url": "https://linear.app/team/issue/ENG-42",
    "assignee": {"name": "Alice"},
    "updatedAt": "2025-01-15T10:30:00.000Z",
    "comments": {"totalCount": 3},
}


class TestParseTicket:
    def test_parses_full_node(self):
        ticket = _parse_ticket(_SAMPLE_NODE)
        assert ticket.id == "issue_1"
        assert ticket.identifier == "ENG-42"
        assert ticket.title == "Fix the bug"
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.branch_name == "eng-42-fix-the-bug"
        assert ticket.url == "https://linear.app/team/issue/ENG-42"
        assert ticket.assignee == "Alice"
        assert ticket.unread_comment_count == 3

    def test_missing_branch_name_defaults_empty(self):
        node = {**_SAMPLE_NODE, "branchName": None}
        ticket = _parse_ticket(node)
        assert ticket.branch_name == ""

    def test_missing_assignee_returns_none(self):
        node = {**_SAMPLE_NODE, "assignee": None}
        ticket = _parse_ticket(node)
        assert ticket.assignee is None

    def test_missing_comments_defaults_zero(self):
        node = {**_SAMPLE_NODE, "comments": None}
        ticket = _parse_ticket(node)
        assert ticket.unread_comment_count == 0

    def test_updated_at_is_utc_datetime(self):
        from datetime import datetime

        ticket = _parse_ticket(_SAMPLE_NODE)
        assert isinstance(ticket.updated_at, datetime)
        assert ticket.updated_at.tzinfo == UTC

    def test_returns_ticket_instance(self):
        ticket = _parse_ticket(_SAMPLE_NODE)
        assert isinstance(ticket, Ticket)


# ---------------------------------------------------------------------------
# fetch_my_issues
# ---------------------------------------------------------------------------


class TestFetchMyIssues:
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

    def _make_response(self, nodes: list[dict]) -> dict:
        return {"viewer": {"assignedIssues": {"nodes": nodes}}}

    async def test_returns_tickets(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = self._make_response([_SAMPLE_NODE])

        tickets = await client.fetch_my_issues("team_123")
        assert len(tickets) == 1
        assert tickets[0].identifier == "ENG-42"

    async def test_empty_response(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = self._make_response([])

        tickets = await client.fetch_my_issues("team_123")
        assert tickets == []

    async def test_multiple_issues(self, connected):
        client, mock_session = connected
        node2 = {**_SAMPLE_NODE, "id": "issue_2", "identifier": "ENG-43"}
        mock_session.execute.return_value = self._make_response([_SAMPLE_NODE, node2])

        tickets = await client.fetch_my_issues("team_123")
        assert len(tickets) == 2
        assert tickets[1].identifier == "ENG-43"

    async def test_passes_team_id_variable(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = self._make_response([])

        await client.fetch_my_issues("team_abc")
        _, kwargs = mock_session.execute.call_args
        assert kwargs["variable_values"] == {"teamId": "team_abc"}

    async def test_propagates_auth_error(self, connected):
        client, mock_session = connected
        exc = TransportServerError("401 Unauthorized")
        exc.code = 401
        mock_session.execute.side_effect = exc

        with pytest.raises(LinearAuthError):
            await client.fetch_my_issues("team_123")

    async def test_propagates_network_error(self, connected):
        client, mock_session = connected
        mock_session.execute.side_effect = ConnectionError("timeout")

        with pytest.raises(LinearNetworkError):
            await client.fetch_my_issues("team_123")


# ---------------------------------------------------------------------------
# _parse_comment
# ---------------------------------------------------------------------------

_SAMPLE_COMMENT_NODE = {
    "id": "comment_1",
    "body": "Looks good!",
    "createdAt": "2025-06-01T12:00:00.000Z",
    "updatedAt": "2025-06-01T13:00:00.000Z",
    "user": {"name": "Bob"},
}


class TestParseComment:
    def test_parses_full_node(self):
        comment = _parse_comment(_SAMPLE_COMMENT_NODE)
        assert comment.id == "comment_1"
        assert comment.body == "Looks good!"
        assert comment.user_name == "Bob"
        assert comment.is_read is False

    def test_missing_user_defaults_to_unknown(self):
        node = {**_SAMPLE_COMMENT_NODE, "user": None}
        comment = _parse_comment(node)
        assert comment.user_name == "Unknown"

    def test_missing_user_name_defaults_to_unknown(self):
        node = {**_SAMPLE_COMMENT_NODE, "user": {}}
        comment = _parse_comment(node)
        assert comment.user_name == "Unknown"

    def test_missing_body_defaults_to_empty(self):
        node = {**_SAMPLE_COMMENT_NODE}
        del node["body"]
        comment = _parse_comment(node)
        assert comment.body == ""

    def test_missing_updated_at_falls_back_to_created_at(self):
        node = {**_SAMPLE_COMMENT_NODE}
        del node["updatedAt"]
        comment = _parse_comment(node)
        assert comment.updated_at == comment.created_at

    def test_created_at_is_utc_datetime(self):
        from datetime import datetime

        comment = _parse_comment(_SAMPLE_COMMENT_NODE)
        assert isinstance(comment.created_at, datetime)
        assert comment.created_at.tzinfo == UTC

    def test_updated_at_is_utc_datetime(self):
        from datetime import datetime

        comment = _parse_comment(_SAMPLE_COMMENT_NODE)
        assert isinstance(comment.updated_at, datetime)
        assert comment.updated_at.tzinfo == UTC

    def test_returns_comment_instance(self):
        comment = _parse_comment(_SAMPLE_COMMENT_NODE)
        assert isinstance(comment, Comment)


# ---------------------------------------------------------------------------
# fetch_issue_comments
# ---------------------------------------------------------------------------


class TestFetchIssueComments:
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

    def _make_response(self, nodes: list[dict]) -> dict:
        return {"issue": {"comments": {"nodes": nodes}}}

    async def test_returns_comments(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = self._make_response([_SAMPLE_COMMENT_NODE])

        comments = await client.fetch_issue_comments("issue_1")
        assert len(comments) == 1
        assert comments[0].body == "Looks good!"

    async def test_empty_response(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = self._make_response([])

        comments = await client.fetch_issue_comments("issue_1")
        assert comments == []

    async def test_multiple_comments(self, connected):
        client, mock_session = connected
        node2 = {**_SAMPLE_COMMENT_NODE, "id": "comment_2", "body": "LGTM"}
        mock_session.execute.return_value = self._make_response(
            [_SAMPLE_COMMENT_NODE, node2]
        )

        comments = await client.fetch_issue_comments("issue_1")
        assert len(comments) == 2
        assert comments[1].body == "LGTM"

    async def test_passes_issue_id_variable(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = self._make_response([])

        await client.fetch_issue_comments("issue_abc")
        _, kwargs = mock_session.execute.call_args
        assert kwargs["variable_values"] == {"issueId": "issue_abc"}

    async def test_null_issue_raises_query_error(self, connected):
        client, mock_session = connected
        mock_session.execute.return_value = {"issue": None}

        with pytest.raises(LinearQueryError, match="Issue not found"):
            await client.fetch_issue_comments("bad_id")

    async def test_propagates_auth_error(self, connected):
        client, mock_session = connected
        exc = TransportServerError("401 Unauthorized")
        exc.code = 401
        mock_session.execute.side_effect = exc

        with pytest.raises(LinearAuthError):
            await client.fetch_issue_comments("issue_1")

    async def test_propagates_network_error(self, connected):
        client, mock_session = connected
        mock_session.execute.side_effect = ConnectionError("timeout")

        with pytest.raises(LinearNetworkError):
            await client.fetch_issue_comments("issue_1")
