"""Application configuration — loads and saves ~/.config/tt-tmux/config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

__all__ = [
    "CONFIG_PATH",
    "AppConfig",
    "ConfigError",
    "ProjectConfig",
    "load_config",
    "save_config",
]

CONFIG_PATH = Path.home() / ".config" / "tt-tmux" / "config.toml"


class ConfigError(Exception):
    """Raised when the config file is missing, unreadable, or malformed."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass
class ProjectConfig:
    """Configuration for a single project (git repository)."""

    path: Path
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.path.name


@dataclass
class AppConfig:
    """Validated application configuration."""

    repo_path: Path
    linear_api_key: str | None = None
    linear_team_id: str | None = None
    github_token: str | None = None
    github_repo: str | None = None
    projects: list[ProjectConfig] = field(default_factory=list)


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate the TOML config file at *path*.

    Supports both the legacy ``repo_path`` key (single-project) and the new
    ``[[projects]]`` array (multi-project).  Legacy files are transparently
    migrated in memory; the next ``save_config`` call will persist the new
    format.

    Raises:
        ConfigError: if the file is missing, invalid TOML, or has neither
            ``repo_path`` nor ``[[projects]]``.
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

    if "projects" in data:
        projects = [
            ProjectConfig(
                path=Path(p["path"]).expanduser(),
                name=p.get("name", ""),
            )
            for p in data["projects"]
        ]
        repo_path = projects[0].path
    elif "repo_path" in data:
        repo_path = Path(data["repo_path"]).expanduser()
        projects = [ProjectConfig(path=repo_path)]
    else:
        raise ConfigError(
            f"Config file is missing required key 'repo_path': {path}",
            reason="missing_repo_path",
        )

    return AppConfig(
        repo_path=repo_path,
        linear_api_key=data.get("linear_api_key"),
        linear_team_id=data.get("linear_team_id"),
        github_token=data.get("github_token"),
        github_repo=data.get("github_repo"),
        projects=projects,
    )


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """Atomically write *config* to *path* in TOML format (new ``[[projects]]`` layout).

    Creates parent directories if they don't exist. Writes to a sibling `.tmp`
    file first, then renames it into place so the final file is never partially
    written. Always emits the new multi-project format; ``repo_path`` is never
    written as a top-level key.
    """
    if path is None:
        path = CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    projects = config.projects or [ProjectConfig(path=config.repo_path)]
    data: dict = {"projects": [{"path": str(p.path), "name": p.name} for p in projects]}
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
