"""Help overlay showing all keybindings."""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold cyan]── Navigation ──[/]
  [bold]j / k[/]       Move down / up
  [bold]h / l[/]       Collapse / expand  (directory tree)
  [bold]G[/]           Jump to bottom
  [bold]g g[/]         Jump to top
  [bold]Tab[/]         Next widget
  [bold]Shift+Tab[/]   Previous widget

[bold cyan]── Worktree List ──[/]
  [bold]c[/]   Create worktree
  [bold]d[/]   Delete worktree
  [bold]r[/]   Rename worktree
  [bold]b[/]   Back to directory select
  [bold]F5[/]  Refresh list

[bold cyan]── Search ──[/]
  [bold]/[/]       Open search bar
  [bold]Enter[/]   Apply filter
  [bold]Escape[/]  Clear filter & close

[bold cyan]── Global ──[/]
  [bold]?[/]   Show this help
  [bold]d[/]   Toggle dark / light theme
  [bold]q[/]   Quit

[bold cyan]── Modals ──[/]
  [bold]Escape[/]  Cancel & close
  [bold]Enter[/]   Submit / confirm
  [bold]Tab[/]     Next field
"""


class HelpOverlay(ModalScreen[None]):
    """Modal overlay displaying all available keybindings."""

    BINDINGS = [
        Binding("escape", "dismiss_help", "Close", show=False),
        Binding("question_mark", "dismiss_help", "Close", show=False),
    ]

    def compose(self):
        with Vertical(id="help-dialog"):
            yield Static("Keyboard Shortcuts", classes="modal-title")
            yield Static(HELP_TEXT, id="help-content")

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
