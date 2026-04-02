"""Shared fixtures for widgets tests."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable

from modules.widgets.search_bar import SearchBar
from modules.widgets.vim_data_table import VimDataTable


# ---------------------------------------------------------------------------
# Minimal host apps for isolated widget testing
# ---------------------------------------------------------------------------


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
