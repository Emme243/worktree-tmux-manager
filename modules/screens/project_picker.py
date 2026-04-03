"""Project picker screen — shown on startup when multiple projects are configured."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label

from modules.core.config import AppConfig, ProjectConfig, save_config
from modules.widgets.vim_data_table import VimDataTable


class _ConfirmDeleteModal(ModalScreen[bool]):
    """Simple yes/no confirmation before deleting a project."""

    BINDINGS = [
        Binding("escape", "cancel", "No", show=False),
        Binding("y", "confirm", "Yes", show=False),
    ]

    DEFAULT_CSS = """
    _ConfirmDeleteModal {
        align: center middle;
    }
    #confirm-dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        border: thick $error;
        background: $surface;
    }
    #confirm-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    """

    def __init__(self, project_name: str) -> None:
        super().__init__()
        self._project_name = project_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(f'Delete "{self._project_name}"?')
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", id="yes-btn", variant="error")
                yield Button("No", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)


class ProjectPickerScreen(ModalScreen[ProjectConfig | None]):
    """Project picker shown on startup when multiple projects are configured.

    Keys:
    - ``Enter``   — open selected project's worktree list
    - ``a``       — add a new project via ProjectSetupScreen
    - ``d``       — delete selected project (with confirmation)
    - ``Escape``  — exit the application
    """

    BINDINGS = [
        Binding("escape", "exit_app", "Exit", show=False),
        Binding("a", "add_project", "Add", show=True),
        Binding("d", "delete_project", "Delete", show=True),
    ]

    DEFAULT_CSS = """
    ProjectPickerScreen {
        align: center middle;
    }
    #picker-dialog {
        width: 80;
        height: auto;
        max-height: 30;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #picker-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #picker-table {
        height: auto;
        max-height: 20;
    }
    #picker-footer {
        color: $text-muted;
        margin-top: 1;
        height: 1;
    }
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._pending_delete_idx: int | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Label("Select Project", id="picker-title")
            yield VimDataTable(id="picker-table", cursor_type="row", zebra_stripes=True)
            yield Label("Enter: open  a: add  d: delete  Esc: quit", id="picker-footer")

    def on_mount(self) -> None:
        table = self.query_one("#picker-table", VimDataTable)
        table.add_column("Name", key="name")
        table.add_column("Path", key="path")
        self._populate_table()
        table.focus()

    def _populate_table(self) -> None:
        table = self.query_one("#picker-table", VimDataTable)
        table.clear()
        for project in self._config.projects:
            table.add_row(project.name, str(project.path))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.cursor_row
        if 0 <= row_idx < len(self._config.projects):
            self.dismiss(self._config.projects[row_idx])

    def action_exit_app(self) -> None:
        self.app.exit()

    def action_add_project(self) -> None:
        from modules.screens.project_setup import ProjectSetupScreen

        self.app.push_screen(
            ProjectSetupScreen(mode="add"),
            callback=self._on_project_added,
        )

    def _on_project_added(self, result: Path | None) -> None:
        if result is None:
            return
        self._config.projects.append(ProjectConfig(path=result))
        save_config(self._config)
        self._populate_table()

    def action_delete_project(self) -> None:
        if not self._config.projects:
            return
        table = self.query_one("#picker-table", VimDataTable)
        self._pending_delete_idx = table.cursor_row
        project = self._config.projects[self._pending_delete_idx]
        self.app.push_screen(
            _ConfirmDeleteModal(project.name),
            callback=self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        if not confirmed or self._pending_delete_idx is None:
            self._pending_delete_idx = None
            return
        del self._config.projects[self._pending_delete_idx]
        self._pending_delete_idx = None
        save_config(self._config)
        self._populate_table()
