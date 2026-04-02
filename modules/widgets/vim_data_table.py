"""DataTable with vim-style keyboard navigation."""

from __future__ import annotations

from textual.binding import Binding
from textual.events import Key
from textual.widgets import DataTable


class VimDataTable(DataTable):
    """DataTable supporting j/k/G/gg vim navigation."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]

    _g_pending: bool = False

    def on_key(self, event: Key) -> None:
        if event.key == "g":
            if self._g_pending:
                self._g_pending = False
                self.action_scroll_top()
                event.prevent_default()
                event.stop()
            else:
                self._g_pending = True
                self.set_timer(0.5, self._clear_g_pending)
                event.prevent_default()
                event.stop()
        elif self._g_pending:
            self._g_pending = False

    def _clear_g_pending(self) -> None:
        self._g_pending = False
