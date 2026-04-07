"""GitHub integration package."""

from .client import (
    GitHubAuthError,
    GitHubClient,
    GitHubClientError,
    GitHubNetworkError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

__all__ = [
    "GitHubAuthError",
    "GitHubClient",
    "GitHubClientError",
    "GitHubNetworkError",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
]
