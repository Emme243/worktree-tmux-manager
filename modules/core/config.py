"""Application configuration — loads ~/.config/tt-tmux/config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

__all__ = ["CONFIG_PATH", "AppConfig", "ConfigError", "load_config"]

CONFIG_PATH = Path.home() / ".config" / "tt-tmux" / "config.toml"


class ConfigError(Exception):
    """Raised when the config file is missing, unreadable, or malformed."""


@dataclass
class AppConfig:
    """Validated application configuration."""

    repo_path: Path
    linear_api_key: str | None = None
    linear_team_id: str | None = None
    github_token: str | None = None
    github_repo: str | None = None


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate the TOML config file at *path*.

    Raises:
        ConfigError: if the file is missing, invalid TOML, or missing ``repo_path``.
    """
    if path is None:
        path = CONFIG_PATH

    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\n"
            "Create it at that path. See README for the required format."
        )

    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Config file is not valid TOML: {path}\n{exc}") from exc

    if "repo_path" not in data:
        raise ConfigError(f"Config file is missing required key 'repo_path': {path}")

    return AppConfig(
        repo_path=Path(data["repo_path"]).expanduser(),
        linear_api_key=data.get("linear_api_key"),
        linear_team_id=data.get("linear_team_id"),
        github_token=data.get("github_token"),
        github_repo=data.get("github_repo"),
    )
