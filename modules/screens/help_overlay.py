"""Help overlay showing all keybindings."""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Navigation",
        [
            ("j / k", "Move down / up"),
            ("h / l", "Collapse / expand (directory tree)"),
            ("G", "Jump to bottom"),
            ("g g", "Jump to top"),
            ("Tab", "Next widget"),
            ("Shift+Tab", "Previous widget"),
        ],
    ),
    (
        "Worktree List",
        [
            ("c", "Create worktree"),
            ("d", "Delete worktree"),
            ("n", "Rename worktree"),
            ("b", "Back to directory select"),
            ("r", "Refresh list"),
        ],
    ),
    (
        "Search",
        [
            ("/", "Open search bar"),
            ("Enter", "Apply filter"),
            ("Escape", "Clear filter & close"),
        ],
    ),
    (
        "Global",
        [
            ("?", "Show this help"),
            ("d", "Toggle dark / light theme"),
            ("q", "Quit"),
        ],
    ),
    (
        "Modals",
        [
            ("Escape / q", "Cancel & close"),
            ("Enter", "Submit / confirm"),
            ("Tab", "Next field"),
            ("j / k", "Scroll help content"),
        ],
    ),
]


class HelpOverlay(ModalScreen[None]):
    """Modal overlay displaying all available keybindings."""

    BINDINGS = [
        Binding("escape", "dismiss_help", "Close", show=False),
        Binding("question_mark", "dismiss_help", "Close", show=False),
        Binding("q", "dismiss_help", "Close", show=False),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
    ]

    def compose(self):
        with Vertical(id="help-dialog", classes="modal-info"):
            yield Static("Keyboard Shortcuts", classes="modal-title")
            with VerticalScroll(id="help-content"):
                for i, (section_title, bindings) in enumerate(HELP_SECTIONS):
                    classes = "help-section-title"
                    if i == 0:
                        classes += " first-section"
                    yield Static(
                        f"── {section_title} ──",
                        classes=classes,
                    )
                    for key, description in bindings:
                        with Horizontal(classes="help-row"):
                            yield Static(key, classes="help-key")
                            yield Static(description, classes="help-desc")

    def action_scroll_down(self) -> None:
        self.query_one("#help-content").scroll_down(animate=False)

    def action_scroll_up(self) -> None:
        self.query_one("#help-content").scroll_up(animate=False)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
