"""Modal screen for adding a new worktree."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual_autocomplete import AutoComplete, DropdownItem

from modules.git import GitError, add_worktree, list_branches


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
            yield Label("Branch:")
            branch_input = Input(
                placeholder="type to search branches...", id="branch-input"
            )
            yield branch_input
            yield AutoComplete(
                branch_input, candidates=[], id="branch-autocomplete"
            )
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
            ac = self.query_one("#branch-autocomplete", AutoComplete)
            ac.candidates = [DropdownItem(main=b) for b in sorted(branches)]
        except GitError as e:
            self._branches = set()
            self.notify(f"Failed to load branches: {e}", severity="error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_add()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "confirm-btn":
            self._do_add()

    @work
    async def _do_add(self) -> None:
        branch_value = self.query_one("#branch-input", Input).value.strip()
        if not branch_value:
            self.notify("Branch name is required", severity="error")
            return

        wt_name = branch_value.replace("/", "-")
        parent_dir = Path(self.repo_dir).parent
        wt_path = str(parent_dir / wt_name)

        if branch_value in self._branches:
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
