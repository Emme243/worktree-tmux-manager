"""Linear GraphQL API client."""

from __future__ import annotations

import datetime as dt
from types import TracebackType
from typing import Any

from gql import Client
from gql import gql as gql_query
from gql.transport.exceptions import (
    TransportQueryError,
    TransportServerError,
)
from gql.transport.httpx import HTTPXAsyncTransport

from modules.core.config import AppConfig
from modules.linear.models import Ticket, TicketStatus

__all__ = [
    "LINEAR_API_URL",
    "LinearAuthError",
    "LinearClient",
    "LinearClientError",
    "LinearNetworkError",
    "LinearQueryError",
    "_map_state_type",
    "_parse_ticket",
]

LINEAR_API_URL = "https://api.linear.app/graphql"


# --- Exceptions ---


class LinearClientError(Exception):
    """Base exception for Linear client errors."""


class LinearAuthError(LinearClientError):
    """Raised when authentication fails (invalid/missing API key)."""


class LinearNetworkError(LinearClientError):
    """Raised on transport/connectivity failures."""


class LinearQueryError(LinearClientError):
    """Raised when the GraphQL response contains errors."""

    def __init__(
        self, message: str, errors: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(message)
        self.errors = errors or []


# --- Client ---


class LinearClient:
    """Async GraphQL client for the Linear API.

    Use as an async context manager for connection reuse::

        async with LinearClient(api_key="lin_...") as client:
            result = await client.execute("{ viewer { id } }")
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._transport = HTTPXAsyncTransport(
            url=LINEAR_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        self._client = Client(
            transport=self._transport,
            fetch_schema_from_transport=False,
        )
        self._session: Any = None

    @classmethod
    def from_config(cls, config: AppConfig) -> LinearClient:
        """Create a client from the application config.

        Raises ``LinearAuthError`` if the API key is not configured.
        """
        if config.linear_api_key is None:
            raise LinearAuthError("Linear API key not configured")
        return cls(config.linear_api_key)

    # -- Lifecycle --

    async def connect(self) -> None:
        """Open a persistent session to the Linear API."""
        self._session = await self._client.connect_async(reconnecting=True)

    async def close(self) -> None:
        """Close the session."""
        await self._client.close_async()
        self._session = None

    async def __aenter__(self) -> LinearClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    # -- Query execution --

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query and return the response data.

        Args:
            query: A GraphQL query string.
            variables: Optional mapping of query variables.

        Returns:
            The ``data`` portion of the GraphQL response.

        Raises:
            LinearAuthError: On 401/403 responses.
            LinearNetworkError: On transport/connectivity failures.
            LinearQueryError: When the response contains GraphQL errors.
        """
        parsed = gql_query(query)
        try:
            if self._session is not None:
                return await self._session.execute(parsed, variable_values=variables)
            return await self._client.execute_async(parsed, variable_values=variables)
        except TransportServerError as exc:
            code = _extract_status_code(exc)
            if code in (401, 403):
                raise LinearAuthError(str(exc)) from exc
            raise LinearNetworkError(str(exc)) from exc
        except TransportQueryError as exc:
            raise LinearQueryError(
                str(exc), errors=getattr(exc, "errors", None)
            ) from exc
        except Exception as exc:
            raise LinearNetworkError(str(exc)) from exc

    # -- Domain queries --

    _FETCH_MY_ISSUES_QUERY = """
    query FetchMyIssues($teamId: String!) {
      viewer {
        assignedIssues(
          first: 50
          filter: {
            team: { id: { eq: $teamId } }
            state: { type: { nin: ["completed", "canceled"] } }
          }
        ) {
          nodes {
            id
            identifier
            title
            state { name type }
            branchName
            url
            assignee { name }
            updatedAt
            comments { totalCount }
          }
        }
      }
    }
    """

    async def fetch_my_issues(self, team_id: str) -> list[Ticket]:
        """Fetch issues assigned to the authenticated user for a team.

        Returns tickets in active states (excludes completed and canceled).
        """
        data = await self.execute(
            self._FETCH_MY_ISSUES_QUERY, variables={"teamId": team_id}
        )
        nodes = data["viewer"]["assignedIssues"]["nodes"]
        return [_parse_ticket(node) for node in nodes]


def _extract_status_code(exc: TransportServerError) -> int | None:
    """Best-effort extraction of HTTP status code from a transport error."""
    code = getattr(exc, "code", None)
    if code is not None:
        return int(code)
    # Fall back to parsing the string representation.
    text = str(exc)
    for token in text.split():
        if token.isdigit():
            return int(token)
    return None


# -- Response parsing helpers --

_STATE_TYPE_MAP: dict[str, TicketStatus] = {
    "triage": TicketStatus.NOT_STARTED,
    "backlog": TicketStatus.NOT_STARTED,
    "unstarted": TicketStatus.NOT_STARTED,
    "started": TicketStatus.IN_PROGRESS,
}


def _map_state_type(state_type: str, state_name: str) -> TicketStatus:
    """Map a Linear workflow state type and name to a ``TicketStatus``.

    Linear state *types* are fixed (``triage``, ``backlog``, ``unstarted``,
    ``started``, ``completed``, ``canceled``).  Teams often create custom
    states within the ``started`` type — e.g. "In Review".  We detect those
    by checking whether the state *name* contains "review".
    """
    if state_type == "started" and "review" in state_name.lower():
        return TicketStatus.IN_REVIEW
    return _STATE_TYPE_MAP.get(state_type, TicketStatus.NOT_STARTED)


def _parse_ticket(node: dict[str, Any]) -> Ticket:
    """Convert a raw GraphQL issue node into a ``Ticket``."""
    state = node.get("state") or {}
    assignee_data = node.get("assignee")
    comments_data = node.get("comments") or {}

    return Ticket(
        id=node["id"],
        identifier=node["identifier"],
        title=node["title"],
        status=_map_state_type(state.get("type", ""), state.get("name", "")),
        branch_name=node.get("branchName") or "",
        url=node["url"],
        assignee=assignee_data["name"] if assignee_data else None,
        updated_at=dt.datetime.fromisoformat(node["updatedAt"]).replace(
            tzinfo=dt.UTC
        ),
        unread_comment_count=comments_data.get("totalCount", 0),
    )
