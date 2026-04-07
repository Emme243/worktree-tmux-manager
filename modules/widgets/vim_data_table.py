"""DataTable with vim-style keyboard navigation and group header rows."""

from __future__ import annotations

from textual.binding import Binding
from textual.events import Key
from textual.widgets import DataTable


class VimDataTable(DataTable):
    """DataTable supporting j/k/G/gg vim navigation and non-selectable header rows."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]

    _g_pending: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._header_row_keys: set = set()

    def add_header_row(self, *cells, key=None):
        """Add a non-selectable group header row. Returns the RowKey."""
        row_key = self.add_row(*cells, key=key)
        self._header_row_keys.add(row_key)
        return row_key

    def is_header_row(self, row_index: int) -> bool:
        """Check if the row at the given index is a header row."""
        if row_index < 0 or row_index >= self.row_count:
            return False
        row_key = self.ordered_rows[row_index].key
        return row_key in self._header_row_keys

    def clear(self, columns: bool = False) -> DataTable:
        """Clear all rows and header tracking."""
        self._header_row_keys.clear()
        return super().clear(columns=columns)

    def _skip_headers_forward(self) -> None:
        """If cursor is on a header, move forward until a data row or end."""
        while self.cursor_row < self.row_count - 1 and self.is_header_row(
            self.cursor_row
        ):
            super().action_cursor_down()

    def _skip_headers_backward(self) -> None:
        """If cursor is on a header, move backward until a data row or start."""
        while self.cursor_row > 0 and self.is_header_row(self.cursor_row):
            super().action_cursor_up()

    def action_cursor_down(self) -> None:
        super().action_cursor_down()
        self._skip_headers_forward()

    def action_cursor_up(self) -> None:
        super().action_cursor_up()
        self._skip_headers_backward()

    def action_scroll_top(self) -> None:
        super().action_scroll_top()
        self._skip_headers_forward()

    def action_scroll_bottom(self) -> None:
        super().action_scroll_bottom()
        self._skip_headers_backward()

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
