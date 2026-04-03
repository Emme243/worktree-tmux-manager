"""Project setup screen for first-run and add-project flows."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from modules.core.config import AppConfig, save_config
from modules.git import is_git_repo
from modules.widgets.directory_input import DirectoryInput


class ProjectSetupScreen(ModalScreen[Path | None]):
    """First-run and add-project setup screen.

    Shown when no project is configured (``mode="first_run"``) or when
    the user wants to add another project (``mode="add"``).
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    DEFAULT_CSS = """
    ProjectSetupScreen {
        align: center middle;
    }
    #setup-dialog {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $success;
        background: $surface;
    }
    #setup-error {
        color: $error;
        height: 1;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, mode: Literal["first_run", "add"]) -> None:
        super().__init__()
        self._mode = mode

    def compose(self) -> ComposeResult:
        title = (
            "Welcome \u2014 Select a Repository"
            if self._mode == "first_run"
            else "Add Project"
        )
        with Vertical(id="setup-dialog"):
            yield Label(title, id="setup-title")
            yield DirectoryInput(label="Repository path:")
            yield Static("", id="setup-error")
            yield Button("Confirm", id="confirm-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one(DirectoryInput).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self._do_confirm()

    def on_input_submitted(self, _: Input.Submitted) -> None:
        # Bubbles up from the inner Input inside DirectoryInput
        self._do_confirm()

    def action_cancel(self) -> None:
        if self._mode == "first_run":
            self.app.exit()
        else:
            self.dismiss(None)

    @work
    async def _do_confirm(self) -> None:
        raw = self.query_one(DirectoryInput).value.strip()
        error = self.query_one("#setup-error", Static)
        error.update("")

        if not raw:
            error.update("Please enter a path.")
            return

        path = Path(raw).expanduser().resolve()

        if not path.is_dir():
            error.update(f"Path does not exist or is not a directory: {raw}")
            return

        if not await is_git_repo(str(path)):
            error.update(f"Not a git repository: {raw}")
            return

        save_config(AppConfig(repo_path=path))
        self.dismiss(path)
