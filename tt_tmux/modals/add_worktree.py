"""Modal screen for adding a new worktree."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import Button, Input, Label, Static

from tt_tmux.git import GitError, add_worktree, list_branches


class AddWorktreeModal(ModalScreen[bool]):
    """Modal to add a new worktree."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, repo_dir: str) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self._branches: set[str] = set()

    def compose(self):
        with Vertical(id="modal-dialog"):
            yield Static("Add Worktree", classes="modal-title")
            yield Label("Worktree name:")
            yield Input(placeholder="my-worktree", id="wt-name")
            yield Label("Branch:")
            yield Input(placeholder="type to search branches...", id="branch-input")
            with Horizontal(classes="modal-buttons"):
                yield Button("Create", variant="success", id="confirm-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        self._load_branches()

    @work
    async def _load_branches(self) -> None:
        try:
            branches = await list_branches(self.repo_dir)
            self._branches = set(branches)
            branch_input = self.query_one("#branch-input", Input)
            branch_input.suggester = SuggestFromList(branches, case_sensitive=False)
        except GitError as e:
            self._branches = set()
            self.notify(f"Failed to load branches: {e}", severity="error")

    def on_key(self, event: Key) -> None:
        if event.key == "tab":
            branch_input = self.query_one("#branch-input", Input)
            if branch_input.has_focus and branch_input._suggestion:
                event.stop()
                event.prevent_default()
                branch_input.value = branch_input._suggestion
                branch_input.cursor_position = len(branch_input.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_add()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "confirm-btn":
            self._do_add()

    @work
    async def _do_add(self) -> None:
        wt_name = self.query_one("#wt-name", Input).value.strip()
        if not wt_name:
            self.notify("Worktree name is required", severity="error")
            return

        parent_dir = Path(self.repo_dir).parent
        wt_path = str(parent_dir / wt_name)

        branch_value = self.query_one("#branch-input", Input).value.strip()

        if not branch_value:
            branch = None
            new_branch = None
        elif branch_value in self._branches:
            branch = branch_value
            new_branch = None
        else:
            branch = "dev"
            new_branch = branch_value

        try:
            await add_worktree(self.repo_dir, wt_path, branch, new_branch)
            self.app.notify("Worktree added successfully")
            self.dismiss(True)
        except GitError as e:
            self.notify(f"Failed: {e}", severity="error")

    def action_cancel(self) -> None:
        self.dismiss(False)
