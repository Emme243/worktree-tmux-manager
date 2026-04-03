"""Screen for listing and managing worktrees."""

from __future__ import annotations

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Static

from modules.git import (
    GitError,
    WorktreeInfo,
    list_worktrees,
    populate_worktree_statuses,
)
from modules.modals import (
    AddWorktreeModal,
    RemoveWorktreeModal,
    RenameWorktreeModal,
)
from modules.tmux import (
    TmuxError,
    build_session_config,
    enter_worktree_session,
    is_worktree_session_active,
)
from modules.widgets import SearchBar, VimDataTable


class WorktreeListScreen(Screen):
    """Main dashboard — list and manage worktrees."""

    BINDINGS = [
        Binding("c", "create", "Create"),
        Binding("d", "delete", "Delete"),
        Binding("r", "rename", "Rename"),
        Binding("f5", "refresh", "Refresh"),
    ]

    def __init__(self, repo_dir: str) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self.worktrees: list[WorktreeInfo] = []
        self._tmux_statuses: dict[str, bool] = {}

    def compose(self):
        yield Header()
        with Vertical(id="wt-layout"):
            yield Static(
                f"Worktrees for: {self.repo_dir}",
                id="wt-title",
            )
            yield SearchBar(id="search-bar")
            yield VimDataTable(id="wt-table", cursor_type="row", zebra_stripes=True)
            with Horizontal(id="action-bar"):
                yield Button("\\[C]reate", variant="success", id="create-btn")
                yield Button("\\[D]elete", variant="error", id="delete-btn")
                yield Button("\\[R]ename", variant="warning", id="rename-btn")

    def on_mount(self) -> None:
        table = self.query_one("#wt-table", VimDataTable)
        table.add_column("Name")
        table.add_column("Branch", width=25)
        table.add_column("HEAD")
        table.add_column("Status")
        table.add_column("Working Tree")
        table.add_column("Tmux")
        self.refresh_worktrees()
        table.focus()

    def _get_selected_worktree(self) -> WorktreeInfo | None:
        table = self.query_one("#wt-table", VimDataTable)
        if table.row_count == 0:
            self.notify("No worktrees in table", severity="warning")
            return None
        try:
            row_idx = table.cursor_row
            if row_idx < 0 or row_idx >= len(self.worktrees):
                return None
            return self.worktrees[row_idx]
        except Exception:
            self.notify("No worktree selected", severity="warning")
            return None

    @work(exclusive=True)
    async def refresh_worktrees(self) -> None:
        try:
            self.worktrees = await list_worktrees(self.repo_dir)
        except GitError as e:
            self.notify(f"Failed to list worktrees: {e}", severity="error")
            return
        await populate_worktree_statuses(self.worktrees)
        self._tmux_statuses = {
            wt.name: is_worktree_session_active(wt.name)
            for wt in self.worktrees
            if not wt.is_bare
        }
        table = self.query_one("#wt-table", VimDataTable)
        table.clear()
        for wt in self.worktrees:
            table.add_row(
                wt.name,
                wt.branch,
                wt.head,
                wt.status,
                wt.wt_status_display,
                self._tmux_indicator(wt),
            )

    def _tmux_indicator(self, wt: WorktreeInfo) -> Text:
        if wt.is_bare:
            return Text("-", style="dim")
        active = self._tmux_statuses.get(wt.name, False)
        if active:
            return Text("active", style="bold green")
        return Text("inactive", style="bold red")

    def _on_modal_dismiss(self, result: bool | None) -> None:
        if result:
            self.refresh_worktrees()

    # ── Actions ──

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_enter_worktree()

    def action_enter_worktree(self) -> None:
        wt = self._get_selected_worktree()
        if wt is None:
            return
        if wt.is_bare:
            self.notify("Cannot enter the bare worktree", severity="warning")
            return
        config = build_session_config(wt)
        tmux_error: str | None = None
        with self.app.suspend():
            try:
                enter_worktree_session(config)
            except TmuxError as e:
                tmux_error = str(e)
        if tmux_error:
            self.notify(f"Tmux error: {tmux_error}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "create-btn": self.action_create,
            "delete-btn": self.action_delete,
            "rename-btn": self.action_rename,
        }
        action = actions.get(event.button.id)
        if action:
            action()

    def action_create(self) -> None:
        self.app.push_screen(
            AddWorktreeModal(self.repo_dir), callback=self._on_modal_dismiss
        )

    def action_delete(self) -> None:
        wt = self._get_selected_worktree()
        if wt:
            self.app.push_screen(
                RemoveWorktreeModal(self.repo_dir, wt),
                callback=self._on_modal_dismiss,
            )

    def action_rename(self) -> None:
        wt = self._get_selected_worktree()
        if wt:
            if wt.is_bare:
                self.notify("Cannot rename the main worktree", severity="warning")
                return
            self.app.push_screen(
                RenameWorktreeModal(self.repo_dir, wt.path),
                callback=self._on_modal_dismiss,
            )

    def action_refresh(self) -> None:
        self.refresh_worktrees()

    # ── Vim: Search & Help ──

    def on_key(self, event: Key) -> None:
        if isinstance(self.focused, Input):
            return
        if event.key == "slash":
            self.query_one("#search-bar", SearchBar).show_bar()
            event.prevent_default()
            event.stop()

    def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
        self._filter_worktrees(event.query)

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self._clear_filter()
        self.query_one("#wt-table", VimDataTable).focus()

    def _filter_worktrees(self, query: str) -> None:
        table = self.query_one("#wt-table", VimDataTable)
        table.clear()
        if not query:
            for wt in self.worktrees:
                table.add_row(
                    wt.name,
                    wt.branch,
                    wt.head,
                    wt.status,
                    wt.wt_status_display,
                    self._tmux_indicator(wt),
                )
            return
        q = query.lower()
        matched = False
        for wt in self.worktrees:
            if (
                q in wt.name.lower()
                or q in wt.branch.lower()
                or q in wt.status.lower()
                or q in wt.wt_status_display.lower()
            ):
                table.add_row(
                    wt.name,
                    wt.branch,
                    wt.head,
                    wt.status,
                    wt.wt_status_display,
                    self._tmux_indicator(wt),
                )
                matched = True
        if not matched:
            self.notify("No worktrees match the search", severity="warning")

    def _clear_filter(self) -> None:
        table = self.query_one("#wt-table", VimDataTable)
        table.clear()
        for wt in self.worktrees:
            table.add_row(
                wt.name,
                wt.branch,
                wt.head,
                wt.status,
                wt.wt_status_display,
                self._tmux_indicator(wt),
            )
