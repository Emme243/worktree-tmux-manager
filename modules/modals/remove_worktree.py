"""Modal screen for removing a worktree."""

from __future__ import annotations

from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from modules.git import GitError, WorktreeInfo, remove_worktree


class RemoveWorktreeModal(ModalScreen[bool]):
    """Confirm worktree removal."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
    ]

    def __init__(self, repo_dir: str, worktree: WorktreeInfo) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self.worktree = worktree

    def compose(self):
        with Vertical(id="modal-dialog", classes="modal-destructive"):
            yield Static("Remove Worktree", classes="modal-title")
            yield Label(f"Remove worktree [b]{self.worktree.name}[/b]?")
            if self.worktree.wt_status and not self.worktree.wt_status.is_clean:
                yield Static(
                    "⚠ This worktree has uncommitted changes "
                    f"({self.worktree.wt_status.summary}). "
                    "All changes will be lost.",
                    classes="modal-warning",
                )
            with Horizontal(classes="modal-buttons"):
                yield Button("Remove", variant="error", id="confirm-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "confirm-btn":
            self._do_remove()

    @work
    async def _do_remove(self) -> None:
        try:
            await remove_worktree(self.repo_dir, self.worktree.path, force=True)
            self.app.notify("Worktree removed", severity="error")
            self.dismiss(True)
        except GitError as e:
            self.notify(f"Failed: {e}", severity="error")

    def action_confirm(self) -> None:
        self._do_remove()

    def action_cancel(self) -> None:
        self.dismiss(False)
