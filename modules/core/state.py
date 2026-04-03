"""Application state — persists runtime state to ~/.local/share/tt-tmux/state.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

__all__ = ["STATE_PATH", "AppState", "load_state", "save_state"]

STATE_PATH = Path.home() / ".local" / "share" / "tt-tmux" / "state.json"


@dataclass
class AppState:
    """Runtime application state that persists across sessions."""

    last_project_path: Path | None = None


def load_state(path: Path | None = None) -> AppState:
    """Load state from *path*, returning a default ``AppState`` on any failure.

    Never raises — a missing or corrupt state file is treated as a clean slate.
    The caller is responsible for validating whether the stored path is still
    relevant (e.g., still present in the configured projects list).
    """
    if path is None:
        path = STATE_PATH

    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        raw = data.get("last_project_path")
        last_project_path = Path(raw) if raw is not None else None
        return AppState(last_project_path=last_project_path)
    except Exception:
        return AppState()


def save_state(state: AppState, path: Path | None = None) -> None:
    """Atomically write *state* to *path* as JSON.

    Creates parent directories if they don't exist. Writes to a sibling ``.tmp``
    file first, then renames it into place so the final file is never partially
    written.
    """
    if path is None:
        path = STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "last_project_path": str(state.last_project_path)
        if state.last_project_path is not None
        else None,
    }

    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
