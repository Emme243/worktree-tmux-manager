"""Screen for listing and managing worktrees."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static

from modules.core.config import AppConfig, ProjectConfig
from modules.core.mapping import MappingRegistry
from modules.core.state import AppState, save_state
from modules.git import (
    GitError,
    WorktreeInfo,
    list_worktrees,
    populate_worktree_statuses,
)
from modules.github.models import PullRequest
from modules.linear.models import Ticket, TicketWorkflowState
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

log = logging.getLogger(__name__)

_GROUP_ORDER = [
    TicketWorkflowState.CODING_IN_PROGRESS,
    TicketWorkflowState.WORKTREE_CREATED,
    TicketWorkflowState.NOT_STARTED,
    TicketWorkflowState.UNDER_REVIEW,
]


class WorktreeListScreen(Screen):
    """Main dashboard — list and manage worktrees."""

    BINDINGS = [
        Binding("c", "create", "Create", show=False),
        Binding("d", "delete", "Delete", show=False),
        Binding("n", "rename", "Rename", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("slash", "search", "Search", key_display="/"),
        Binding("p", "switch_project", "Switch project"),
        Binding("S", "settings", "Settings"),
    ]

    def __init__(self, repo_dir: str, config: AppConfig) -> None:
        super().__init__()
        self.repo_dir = repo_dir
        self._config = config
        self.worktrees: list[WorktreeInfo] = []
        self._tmux_statuses: dict[str, bool] = {}
        self._registry = MappingRegistry()
        self._tickets: list[Ticket] = []
        self._prs: list[PullRequest] = []
        self._row_data: list[WorktreeInfo | Ticket | None] = []
        self._clients_initialized = False
        self._linear_client = None
        self._github_client = None

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
                yield Button("Re\\[N]ame", variant="warning", id="rename-btn")
        yield Footer()

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
            if row_idx < 0 or row_idx >= len(self._row_data):
                return None
            item = self._row_data[row_idx]
            if isinstance(item, WorktreeInfo):
                return item
            return None
        except Exception:
            self.notify("No worktree selected", severity="warning")
            return None

    def _get_active_project(self) -> ProjectConfig | None:
        """Find the ProjectConfig matching the current repo_dir."""
        repo_path = Path(self.repo_dir).resolve()
        for p in self._config.projects:
            if p.path.resolve() == repo_path:
                return p
        return None

    async def _init_clients(self) -> None:
        """Lazily initialize Linear and GitHub clients from config."""
        if self._clients_initialized:
            return
        self._clients_initialized = True

        # Linear client
        if self._config.linear_api_key:
            try:
                from modules.linear.cache import CachedLinearClient
                from modules.linear.client import LinearClient

                raw = LinearClient(self._config.linear_api_key)
                self._linear_client = CachedLinearClient(raw)
                await self._linear_client.connect()
            except Exception:
                log.debug("Linear client init failed", exc_info=True)
                self._linear_client = None

        # GitHub client — resolve repo slug from active project or global config
        project = self._get_active_project()
        github_repo = (
            project.github_repo if project else None
        ) or self._config.github_repo
        if self._config.github_token and github_repo:
            try:
                from modules.github.cache import CachedGitHubClient
                from modules.github.client import GitHubClient

                raw = GitHubClient(self._config.github_token, github_repo)
                self._github_client = CachedGitHubClient(raw)
                await self._github_client.connect()
            except Exception:
                log.debug("GitHub client init failed", exc_info=True)
                self._github_client = None

    async def _fetch_linear_tickets(self) -> None:
        """Fetch Linear tickets (safe to call concurrently)."""
        if self._linear_client and self._config.linear_team_id:
            try:
                self._tickets = await self._linear_client.fetch_my_issues(
                    self._config.linear_team_id
                )
            except Exception:
                log.debug("Failed to fetch Linear tickets", exc_info=True)
                self._tickets = []
        else:
            self._tickets = []

    async def _fetch_github_prs(self) -> None:
        """Fetch GitHub PRs (safe to call concurrently)."""
        if self._github_client:
            try:
                self._prs = await self._github_client.fetch_open_prs()
            except Exception:
                log.debug("Failed to fetch GitHub PRs", exc_info=True)
                self._prs = []
        else:
            self._prs = []

    async def _fetch_tickets_and_prs(self) -> None:
        """Fetch tickets and PRs concurrently from configured integrations."""
        await asyncio.gather(
            self._fetch_linear_tickets(),
            self._fetch_github_prs(),
        )

    @work(exclusive=True)
    async def refresh_worktrees(self) -> None:
        # Phase 1: Git data — render table immediately
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
        self._render_grouped_table()

        # Phase 2: API data — fetch concurrently, then re-render with grouping
        await self._init_clients()
        if not self._linear_client and not self._github_client:
            return
        title = self.query_one("#wt-title", Static)
        title.update(f"Worktrees for: {self.repo_dir}  (loading...)")
        await self._fetch_tickets_and_prs()
        self._registry.refresh(self.worktrees, self._tickets, self._prs)
        self._render_grouped_table()
        title.update(f"Worktrees for: {self.repo_dir}")

    def _render_grouped_table(self) -> None:
        """Render worktrees grouped by workflow state with header rows."""
        table = self.query_one("#wt-table", VimDataTable)
        table.clear()
        self._row_data = []

        # Classify worktrees into groups
        groups: dict[TicketWorkflowState, list[WorktreeInfo]] = {
            s: [] for s in _GROUP_ORDER
        }
        for wt in self.worktrees:
            if wt.is_bare:
                groups[TicketWorkflowState.WORKTREE_CREATED].append(wt)
                continue
            state = self._registry.get_workflow_state(wt.path)
            groups[state].append(wt)

        unmatched = self._registry.unmatched_tickets

        for group_state in _GROUP_ORDER:
            items = groups[group_state]
            ghost_tickets = (
                unmatched if group_state == TicketWorkflowState.NOT_STARTED else []
            )

            if not items and not ghost_tickets:
                continue

            count = len(items) + len(ghost_tickets)
            header_text = Text(
                f"  {group_state.value}  ({count})", style="bold italic cyan"
            )
            table.add_header_row(header_text, "", "", "", "", "")
            self._row_data.append(None)

            for wt in items:
                table.add_row(
                    self._styled_name(wt),
                    wt.branch,
                    wt.head,
                    wt.status,
                    wt.wt_status_display,
                    self._tmux_indicator(wt),
                )
                self._row_data.append(wt)

            for ticket in ghost_tickets:
                table.add_row(
                    Text(ticket.identifier, style="dim"),
                    Text(ticket.branch_name, style="dim"),
                    Text("", style="dim"),
                    Text(ticket.status.value, style="dim"),
                    Text("-", style="dim"),
                    Text("-", style="dim"),
                )
                self._row_data.append(ticket)

        # Move cursor to first data row (skip header at row 0)
        if self._row_data:
            for i, item in enumerate(self._row_data):
                if item is not None:
                    table.move_cursor(row=i)
                    break

    def _is_main_worktree(self, wt: WorktreeInfo) -> bool:
        return os.path.realpath(wt.path) == os.path.realpath(self.repo_dir)

    def _styled_name(self, wt: WorktreeInfo) -> str | Text:
        if self._is_main_worktree(wt):
            return Text(wt.name, style="bold yellow")
        return wt.name

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

    def action_switch_project(self) -> None:
        from modules.screens.project_picker import ProjectPickerScreen

        self.app.push_screen(
            ProjectPickerScreen(self._config),
            callback=self._on_project_switched,
        )

    def action_settings(self) -> None:
        from modules.screens.settings import SettingsScreen

        self.app.push_screen(
            SettingsScreen(self._config),
            callback=self._on_settings_dismissed,
        )

    def _on_settings_dismissed(self, result: bool) -> None:
        if result:
            from modules.core.config import load_config

            self._config = load_config()

    def _on_project_switched(self, result: ProjectConfig | None) -> None:
        if result is None:
            return
        self.repo_dir = str(result.path)
        save_state(AppState(last_project_path=result.path))
        self.query_one("#wt-title", Static).update(f"Worktrees for: {self.repo_dir}")
        self._clients_initialized = False
        self._linear_client = None
        self._github_client = None
        self.refresh_worktrees()

    async def on_unmount(self) -> None:
        """Close API clients when leaving the screen."""
        import contextlib

        if self._linear_client:
            with contextlib.suppress(Exception):
                await self._linear_client.close()
        if self._github_client:
            with contextlib.suppress(Exception):
                await self._github_client.close()

    # ── Vim: Search & Help ──

    def action_search(self) -> None:
        self.query_one("#search-bar", SearchBar).show_bar()

    def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
        self._filter_worktrees(event.query)

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self._clear_filter()
        self.query_one("#wt-table", VimDataTable).focus()

    def _filter_worktrees(self, query: str) -> None:
        """Filter worktrees — flattened (no group headers) during search."""
        table = self.query_one("#wt-table", VimDataTable)
        table.clear()
        self._row_data = []
        if not query:
            self._render_grouped_table()
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
                    self._styled_name(wt),
                    wt.branch,
                    wt.head,
                    wt.status,
                    wt.wt_status_display,
                    self._tmux_indicator(wt),
                )
                self._row_data.append(wt)
                matched = True
        if not matched:
            self.notify("No worktrees match the search", severity="warning")

    def _clear_filter(self) -> None:
        self._render_grouped_table()
