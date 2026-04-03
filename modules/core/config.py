"""Application configuration — loads and saves ~/.config/tt-tmux/config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w

__all__ = ["CONFIG_PATH", "AppConfig", "ConfigError", "load_config", "save_config"]

CONFIG_PATH = Path.home() / ".config" / "tt-tmux" / "config.toml"


class ConfigError(Exception):
    """Raised when the config file is missing, unreadable, or malformed."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


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
            "Create it at that path. See README for the required format.",
            reason="missing_file",
        )

    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Config file is not valid TOML: {path}\n{exc}", reason="invalid_toml"
        ) from exc

    if "repo_path" not in data:
        raise ConfigError(
            f"Config file is missing required key 'repo_path': {path}",
            reason="missing_repo_path",
        )

    return AppConfig(
        repo_path=Path(data["repo_path"]).expanduser(),
        linear_api_key=data.get("linear_api_key"),
        linear_team_id=data.get("linear_team_id"),
        github_token=data.get("github_token"),
        github_repo=data.get("github_repo"),
    )


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """Atomically write *config* to *path* in TOML format.

    Creates parent directories if they don't exist. Writes to a sibling `.tmp`
    file first, then renames it into place so the final file is never partially
    written.
    """
    if path is None:
        path = CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {"repo_path": str(config.repo_path)}
    if config.linear_api_key is not None:
        data["linear_api_key"] = config.linear_api_key
    if config.linear_team_id is not None:
        data["linear_team_id"] = config.linear_team_id
    if config.github_token is not None:
        data["github_token"] = config.github_token
    if config.github_repo is not None:
        data["github_repo"] = config.github_repo

    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("wb") as fh:
            tomli_w.dump(data, fh)
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
