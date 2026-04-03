"""Tests for modules.widgets.directory_input."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Input, Label
from textual_autocomplete import AutoComplete

from modules.widgets.directory_input import DirectoryInput, _get_directory_suggestions

from .conftest import DirectoryInputApp

# ---------------------------------------------------------------------------
# _get_directory_suggestions — pure unit tests (no Textual app needed)
# ---------------------------------------------------------------------------


class TestGetDirectorySuggestions:
    def test_no_slash_returns_empty(self):
        assert _get_directory_suggestions("abc") == []

    def test_empty_string_returns_empty(self):
        assert _get_directory_suggestions("") == []

    def test_returns_only_directories(self, tmp_path):
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta").mkdir()
        (tmp_path / "gamma.txt").touch()

        names = [item.value for item in _get_directory_suggestions(f"{tmp_path}/")]
        assert "alpha/" in names
        assert "beta/" in names
        assert "gamma.txt" not in names
        assert "gamma.txt/" not in names

    def test_appends_slash_to_each_name(self, tmp_path):
        (tmp_path / "foo").mkdir()
        (tmp_path / "bar").mkdir()

        items = _get_directory_suggestions(f"{tmp_path}/")
        assert all(item.value.endswith("/") for item in items)

    def test_tilde_expansion_lists_home_subdirs(self):
        items = _get_directory_suggestions("~/")
        home = Path.home()
        home_subdirs = {p.name + "/" for p in home.iterdir() if p.is_dir()}
        result_names = {item.value for item in items}
        # All returned names must be actual home subdirectories
        assert result_names.issubset(home_subdirs)
        # At least some home subdirs should be returned
        assert len(items) > 0

    def test_nonexistent_parent_returns_empty(self):
        assert _get_directory_suggestions("/this/path/does/not/exist/anywhere/") == []

    def test_sorted_case_insensitively(self, tmp_path):
        (tmp_path / "Zebra").mkdir()
        (tmp_path / "alpha").mkdir()
        (tmp_path / "Middle").mkdir()

        names = [item.value for item in _get_directory_suggestions(f"{tmp_path}/")]
        assert names == sorted(names, key=str.lower)

    def test_root_slash_returns_entries(self):
        items = _get_directory_suggestions("/")
        assert len(items) > 0
        assert all(item.value.endswith("/") for item in items)

    def test_partial_path_scans_parent_directory(self, tmp_path):
        (tmp_path / "projects").mkdir()
        (tmp_path / "personal").mkdir()

        # User has typed up to the parent dir with a partial child name
        names = [item.value for item in _get_directory_suggestions(f"{tmp_path}/pro")]
        assert "projects/" in names
        assert "personal/" in names

    def test_tilde_with_partial_segment(self):
        # ~/pr should scan home dir and return its subdirs
        items = _get_directory_suggestions("~/pr")
        home = Path.home()
        home_subdirs = {p.name + "/" for p in home.iterdir() if p.is_dir()}
        result_names = {item.value for item in items}
        assert result_names.issubset(home_subdirs)


# ---------------------------------------------------------------------------
# DirectoryInput.compose — widget structure
# ---------------------------------------------------------------------------


class TestDirectoryInputCompose:
    async def test_contains_label(self, directory_input_app):
        async with directory_input_app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            assert widget.query_one(Label) is not None

    async def test_contains_input(self, directory_input_app):
        async with directory_input_app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            assert widget.query_one("#dir-input", Input) is not None

    async def test_contains_autocomplete(self, directory_input_app):
        async with directory_input_app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            assert widget.query_one("#dir-autocomplete", AutoComplete) is not None

    async def test_custom_label_text(self):
        app = DirectoryInputApp(label="Repository path:")
        async with app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            label = widget.query_one(Label)
            assert "Repository path:" in label.render().plain

    async def test_initial_value_set_on_input(self):
        app = DirectoryInputApp(value="/some/path")
        async with app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            inp = widget.query_one("#dir-input", Input)
            assert inp.value == "/some/path"


# ---------------------------------------------------------------------------
# DirectoryInput.value — property
# ---------------------------------------------------------------------------


class TestDirectoryInputValue:
    async def test_value_returns_input_content(self, directory_input_app):
        async with directory_input_app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            inp = widget.query_one("#dir-input", Input)
            inp.value = "/home/user/projects"
            assert widget.value == "/home/user/projects"

    async def test_value_reflects_input_change(self, directory_input_app):
        async with directory_input_app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            inp = widget.query_one("#dir-input", Input)
            inp.value = "~/new/path"
            assert widget.value == "~/new/path"

    async def test_value_empty_by_default(self, directory_input_app):
        async with directory_input_app.run_test() as pilot:
            widget = pilot.app.query_one(DirectoryInput)
            assert widget.value == ""
