"""Tests for modules.core.state — AppState, load_state, save_state."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from unittest.mock import patch

from modules.core.state import STATE_PATH, AppState, load_state, save_state

# ---------------------------------------------------------------------------
# AppState
# ---------------------------------------------------------------------------


class TestAppState:
    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(AppState)

    def test_default_last_project_path_is_none(self):
        assert AppState().last_project_path is None

    def test_explicit_path_stored(self):
        p = Path("/a/b")
        assert AppState(last_project_path=p).last_project_path == p

    def test_field_is_path_object(self):
        state = AppState(last_project_path=Path("/x/y"))
        assert isinstance(state.last_project_path, Path)


# ---------------------------------------------------------------------------
# STATE_PATH constant
# ---------------------------------------------------------------------------


class TestStatePath:
    def test_state_path_value(self):
        expected = Path.home() / ".local" / "share" / "tt-tmux" / "state.json"
        assert expected == STATE_PATH


# ---------------------------------------------------------------------------
# load_state — missing file
# ---------------------------------------------------------------------------


class TestLoadStateMissingFile:
    def test_returns_app_state_instance(self, tmp_path):
        result = load_state(tmp_path / "nonexistent.json")
        assert isinstance(result, AppState)

    def test_last_project_path_is_none(self, tmp_path):
        result = load_state(tmp_path / "nonexistent.json")
        assert result.last_project_path is None

    def test_does_not_raise(self, tmp_path):
        load_state(tmp_path / "nonexistent.json")  # must not raise


# ---------------------------------------------------------------------------
# load_state — corrupt / unexpected file contents
# ---------------------------------------------------------------------------


class TestLoadStateCorruptFile:
    def test_returns_default_on_invalid_json(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("not json {{{", encoding="utf-8")
        result = load_state(f)
        assert result == AppState()

    def test_returns_default_on_wrong_type(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        result = load_state(f)
        assert result == AppState()

    def test_returns_default_on_missing_key(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("{}", encoding="utf-8")
        result = load_state(f)
        assert result.last_project_path is None


# ---------------------------------------------------------------------------
# load_state — success
# ---------------------------------------------------------------------------


class TestLoadStateSuccess:
    def test_loads_path_from_json(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(
            json.dumps({"last_project_path": "/some/project"}), encoding="utf-8"
        )
        result = load_state(f)
        assert result.last_project_path == Path("/some/project")

    def test_last_project_path_is_path_object(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(
            json.dumps({"last_project_path": "/some/project"}), encoding="utf-8"
        )
        result = load_state(f)
        assert isinstance(result.last_project_path, Path)

    def test_null_last_project_path(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(json.dumps({"last_project_path": None}), encoding="utf-8")
        result = load_state(f)
        assert result.last_project_path is None

    def test_uses_default_state_path(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"last_project_path": "/p"}), encoding="utf-8")
        with patch("modules.core.state.STATE_PATH", state_file):
            result = load_state()
        assert result.last_project_path == Path("/p")


# ---------------------------------------------------------------------------
# save_state
# ---------------------------------------------------------------------------


class TestSaveState:
    def test_file_is_written(self, tmp_path):
        f = tmp_path / "state.json"
        save_state(AppState(last_project_path=Path("/repo")), f)
        assert f.exists()

    def test_round_trip_with_path(self, tmp_path):
        f = tmp_path / "state.json"
        original = AppState(last_project_path=Path("/repo/proj"))
        save_state(original, f)
        loaded = load_state(f)
        assert loaded.last_project_path == original.last_project_path

    def test_round_trip_with_none(self, tmp_path):
        f = tmp_path / "state.json"
        save_state(AppState(), f)
        loaded = load_state(f)
        assert loaded.last_project_path is None

    def test_creates_parent_directories(self, tmp_path):
        f = tmp_path / "nested" / "dirs" / "state.json"
        save_state(AppState(last_project_path=Path("/x")), f)
        assert f.exists()

    def test_no_tmp_file_left_on_success(self, tmp_path):
        f = tmp_path / "state.json"
        save_state(AppState(), f)
        assert not f.with_name(f.name + ".tmp").exists()

    def test_json_content_has_expected_key(self, tmp_path):
        f = tmp_path / "state.json"
        save_state(AppState(last_project_path=Path("/some/path")), f)
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "last_project_path" in data
        assert data["last_project_path"] == "/some/path"

    def test_json_content_null_for_none(self, tmp_path):
        f = tmp_path / "state.json"
        save_state(AppState(), f)
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["last_project_path"] is None

    def test_uses_default_state_path(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch("modules.core.state.STATE_PATH", state_file):
            save_state(AppState(last_project_path=Path("/p")))
        assert state_file.exists()
