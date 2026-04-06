"""Shared fixtures for widgets tests."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from modules.widgets.directory_input import DirectoryInput
from modules.widgets.search_bar import SearchBar
from modules.widgets.secret_input import SecretInput
from modules.widgets.vim_data_table import VimDataTable

# ---------------------------------------------------------------------------
# Minimal host apps for isolated widget testing
# ---------------------------------------------------------------------------


class DirectoryInputApp(App):
    """Host app that mounts a single DirectoryInput."""

    CSS = """
    DirectoryInput { height: auto; }
    """

    def __init__(self, label: str = "Path:", value: str = "") -> None:
        super().__init__()
        self._label = label
        self._value = value

    def compose(self) -> ComposeResult:
        yield DirectoryInput(label=self._label, value=self._value)


class SearchBarApp(App):
    """Host app that mounts a single SearchBar."""

    CSS = """
    SearchBar { height: auto; }
    """

    def compose(self) -> ComposeResult:
        yield SearchBar()


class VimDataTableApp(App):
    """Host app that mounts a VimDataTable with sample rows."""

    CSS = """
    VimDataTable { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield VimDataTable()

    def on_mount(self) -> None:
        table = self.query_one(VimDataTable)
        table.add_columns("Name", "Value")
        for i in range(10):
            table.add_row(f"item-{i}", f"val-{i}")
        table.cursor_type = "row"


class SecretInputApp(App):
    """Host app that mounts a single SecretInput."""

    CSS = """
    SecretInput { height: auto; }
    """

    def __init__(
        self, label: str = "API Key:", placeholder: str = "", hint: str = ""
    ) -> None:
        super().__init__()
        self._label = label
        self._placeholder = placeholder
        self._hint = hint

    def compose(self) -> ComposeResult:
        yield SecretInput(
            label=self._label, placeholder=self._placeholder, hint=self._hint
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def search_bar_app():
    """Return a SearchBarApp instance."""
    return SearchBarApp()


@pytest.fixture
def vim_table_app():
    """Return a VimDataTableApp instance."""
    return VimDataTableApp()


@pytest.fixture
def directory_input_app():
    """Return a DirectoryInputApp instance."""
    return DirectoryInputApp()


@pytest.fixture
def secret_input_app():
    """Return a SecretInputApp instance."""
    return SecretInputApp()
