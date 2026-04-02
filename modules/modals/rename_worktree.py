"""Modal screen for renaming a worktree."""

from __future__ import annotations

import os

from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from modules.git import GitError, move_worktree


class RenameWorktreeModal(ModalScreen[bool]):
    """Rename a worktree (change its directory name)."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, repo_dir: str, wt_path: str) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self.wt_path = wt_path
        self.current_name = os.path.basename(wt_path)
        self.parent_dir = os.path.dirname(wt_path)

    def compose(self):
        with Vertical(id="modal-dialog", classes="modal-rename"):
            yield Static("Rename Worktree", classes="modal-title")
            yield Label(f"Current name: {self.current_name}")
            yield Label("New name:")
            yield Input(value=self.current_name, id="new-name")
            with Horizontal(classes="modal-buttons"):
                yield Button("Rename", variant="warning", id="confirm-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_rename()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "confirm-btn":
            self._do_rename()

    @work
    async def _do_rename(self) -> None:
        new_name = self.query_one("#new-name", Input).value.strip()
        if not new_name:
            self.notify("New name is required", severity="error")
            return
        new_path = os.path.join(self.parent_dir, new_name)
        try:
            await move_worktree(self.repo_dir, self.wt_path, new_path)
            self.app.notify("Worktree renamed", severity="warning")
            self.dismiss(True)
        except GitError as e:
            self.notify(f"Failed: {e}", severity="error")

    def action_cancel(self) -> None:
        self.dismiss(False)
