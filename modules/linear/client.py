"""Linear GraphQL API client."""

from __future__ import annotations

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

__all__ = [
    "LINEAR_API_URL",
    "LinearAuthError",
    "LinearClient",
    "LinearClientError",
    "LinearNetworkError",
    "LinearQueryError",
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
