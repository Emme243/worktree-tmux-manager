"""Toggleable search/filter bar for worktree lists."""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label


class SearchBar(Widget):
    """A search bar that can be shown/hidden with filter messages."""

    BINDINGS = [Binding("escape", "dismiss", "Close Search", show=False)]

    class Submitted(Message):
        """Emitted when the user submits a search query."""

        def __init__(self, query: str) -> None:
            self.query = query
            super().__init__()

    class Dismissed(Message):
        """Emitted when the user dismisses the search bar."""

    def compose(self):
        with Horizontal():
            yield Label(" / ", id="search-icon")
            yield Input(placeholder="Search worktrees...", id="search-input")

    def show_bar(self) -> None:
        self.display = True
        self.query_one("#search-input", Input).value = ""
        self.query_one("#search-input", Input).focus()

    def hide_bar(self) -> None:
        self.display = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self.post_message(self.Submitted(event.value.strip()))

    def action_dismiss(self) -> None:
        self.hide_bar()
        self.post_message(self.Dismissed())
