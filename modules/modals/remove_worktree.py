"""Modal screen for removing a worktree."""

from __future__ import annotations

from dataclasses import dataclass

from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, Static

from modules.git import GitError, WorktreeInfo, delete_branch, remove_worktree
from modules.git.operations import run_git


@dataclass
class RemoveWorktreeResult:
    """Result of a worktree removal operation."""

    success: bool
    branch_deleted: bool = False
    branch_delete_error: str | None = None


class RemoveWorktreeModal(ModalScreen[RemoveWorktreeResult | bool]):
    """Confirm worktree removal."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("q", "cancel", "Cancel", show=False),
        Binding("d", "confirm", "Delete", show=False),
    ]

    def __init__(self, repo_dir: str, worktree: WorktreeInfo) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self.worktree = worktree

    @property
    def _has_branch(self) -> bool:
        return not (self.worktree.is_detached or self.worktree.is_bare)

    @property
    def _is_dirty(self) -> bool:
        return bool(self.worktree.wt_status and not self.worktree.wt_status.is_clean)

    def compose(self):
        with Vertical(id="modal-dialog", classes="modal-destructive"):
            yield Static("Delete Worktree", classes="modal-title")
            yield Label(f"Delete worktree [b]{self.worktree.name}[/b]?")
            if self._is_dirty:
                yield Static(
                    "⚠ This worktree has uncommitted changes "
                    f"({self.worktree.wt_status.summary}).",
                    classes="modal-warning",
                )
            if self._has_branch:
                yield Checkbox(
                    f"Delete local branch ({self.worktree.branch})",
                    value=True,
                    id="delete-branch-cb",
                )
            yield Checkbox("Force delete", value=False, id="force-cb")
            yield Static("", id="dynamic-warning", classes="modal-warning")
            with Horizontal(classes="modal-buttons"):
                yield Button("\\[D]elete", variant="error", id="confirm-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        self._update_dynamic_warning()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self._update_dynamic_warning()

    def _update_dynamic_warning(self) -> None:
        force = self.query_one("#force-cb", Checkbox).value
        delete_branch_checked = (
            self._has_branch and self.query_one("#delete-branch-cb", Checkbox).value
        )

        warnings: list[str] = []

        if self._is_dirty and not force:
            warnings.append(
                "Worktree has uncommitted changes. Enable force to proceed."
            )
        elif self._is_dirty and force:
            warnings.append("⚠ Uncommitted changes will be permanently lost.")

        if self.worktree.locked and not force:
            warnings.append("This worktree is locked. Enable force to remove it.")
        elif self.worktree.locked and force:
            warnings.append("⚠ Locked worktree will be force-removed.")

        if delete_branch_checked and not force:
            warnings.append("Branch will only be deleted if fully merged into HEAD.")
        elif delete_branch_checked and force:
            warnings.append("⚠ Branch will be deleted even if it has unmerged commits.")

        widget = self.query_one("#dynamic-warning", Static)
        if warnings:
            widget.update("\n".join(warnings))
            widget.display = True
        else:
            widget.update("")
            widget.display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "confirm-btn":
            self._do_remove()

    @work
    async def _do_remove(self) -> None:
        force = self.query_one("#force-cb", Checkbox).value
        should_delete_branch = (
            self._has_branch and self.query_one("#delete-branch-cb", Checkbox).value
        )
        branch_name = self.worktree.branch if should_delete_branch else None

        # Step 1: Remove worktree (must happen before branch deletion)
        try:
            if self.worktree.locked and force:
                await run_git(
                    self.repo_dir,
                    "worktree",
                    "remove",
                    "--force",
                    "--force",
                    self.worktree.path,
                )
            else:
                await remove_worktree(self.repo_dir, self.worktree.path, force=force)
        except GitError as e:
            self.notify(f"Failed: {e}", severity="error")
            return

        # Step 2: Delete branch (only after worktree is removed)
        branch_deleted = False
        branch_error = None
        if branch_name:
            try:
                await delete_branch(self.repo_dir, branch_name, force=force)
                branch_deleted = True
            except GitError as e:
                branch_error = str(e)
                self.notify(
                    f"Worktree deleted, but branch deletion failed: {e}",
                    severity="warning",
                )

        if not branch_error:
            msg = (
                "Worktree and branch deleted" if branch_deleted else "Worktree deleted"
            )
            self.app.notify(msg, severity="error")

        self.dismiss(
            RemoveWorktreeResult(
                success=True,
                branch_deleted=branch_deleted,
                branch_delete_error=branch_error,
            )
        )

    def action_confirm(self) -> None:
        self._do_remove()

    def action_cancel(self) -> None:
        self.dismiss(False)
