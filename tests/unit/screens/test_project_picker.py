"""Tests for modules.screens.project_picker — ProjectPickerScreen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App
from textual.widgets import Label

from modules.core.config import AppConfig, ProjectConfig
from modules.screens.project_picker import ProjectPickerScreen, _ConfirmDeleteModal
from modules.widgets.vim_data_table import VimDataTable

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class ProjectPickerTestApp(App[None]):
    """Minimal host app that pushes ProjectPickerScreen and captures its result."""

    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: ProjectPickerScreen) -> None:
        super().__init__()
        self._screen = screen
        self.modal_result: Any = _UNSET

    def on_mount(self) -> None:
        self.push_screen(self._screen, callback=self._on_dismiss)

    def _on_dismiss(self, result: ProjectConfig | None) -> None:
        self.modal_result = result


async def _wait_ready(pilot, app) -> None:
    await pilot.pause()
    await pilot.pause()
    await app.workers.wait_for_complete()


def _make_config(projects: list[ProjectConfig]) -> AppConfig:
    return AppConfig(repo_path=projects[0].path, projects=projects)


# ---------------------------------------------------------------------------
# Compose / Init
# ---------------------------------------------------------------------------


class TestProjectPickerScreenCompose:
    async def test_renders_title(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            title = app.screen.query_one("#picker-title", Label)
            assert "Select Project" in title.render().plain

    async def test_renders_table(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            assert table is not None

    async def test_table_has_name_and_path_columns(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            col_keys = [col.key for col in table.columns.values()]
            assert "name" in col_keys
            assert "path" in col_keys

    async def test_table_row_count_matches_projects(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            assert table.row_count == len(sample_projects)

    async def test_table_shows_project_names(self, sample_projects):
        from textual.coordinate import Coordinate

        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            # Check name column (col 0) for each row
            names = [
                str(table.get_cell_at(Coordinate(i, 0))) for i in range(table.row_count)
            ]
            assert "alpha" in names
            assert "beta" in names


# ---------------------------------------------------------------------------
# Selection — Enter dismisses with ProjectConfig
# ---------------------------------------------------------------------------


class TestProjectPickerScreenSelection:
    async def test_enter_dismisses_with_first_project(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            table.focus()
            table.move_cursor(row=0)
            await pilot.press("enter")
            await pilot.pause()
            assert app.modal_result is sample_projects[0]

    async def test_enter_dismisses_with_second_project(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            table.focus()
            table.move_cursor(row=1)
            await pilot.press("enter")
            await pilot.pause()
            assert app.modal_result is sample_projects[1]


# ---------------------------------------------------------------------------
# Add project — 'a' key
# ---------------------------------------------------------------------------


class TestProjectPickerScreenAddProject:
    async def test_a_opens_project_setup_screen(self, sample_projects):
        from modules.screens.project_setup import ProjectSetupScreen

        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, ProjectSetupScreen)

    async def test_add_project_appends_to_config_and_refreshes(
        self, sample_projects, mock_save_config_picker, tmp_path
    ):
        new_path = tmp_path / "gamma"
        new_path.mkdir()
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            initial_row_count = app.screen.query_one(
                "#picker-table", VimDataTable
            ).row_count
            # Simulate _on_project_added callback directly
            app.screen._on_project_added(new_path)
            await pilot.pause()
            table = app.screen.query_one("#picker-table", VimDataTable)
            assert table.row_count == initial_row_count + 1
            mock_save_config_picker.assert_called_once()

    async def test_add_project_none_result_does_not_change_config(
        self, sample_projects, mock_save_config_picker
    ):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            app.screen._on_project_added(None)
            await pilot.pause()
            mock_save_config_picker.assert_not_called()
            assert len(config.projects) == 2


# ---------------------------------------------------------------------------
# Delete project — 'd' key
# ---------------------------------------------------------------------------


class TestProjectPickerScreenDelete:
    async def test_d_opens_confirm_modal(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            table.focus()
            table.move_cursor(row=0)
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, _ConfirmDeleteModal)

    async def test_confirm_delete_removes_project(
        self, sample_projects, mock_save_config_picker
    ):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            table = app.screen.query_one("#picker-table", VimDataTable)
            table.focus()
            table.move_cursor(row=0)
            # Set pending delete index and call confirm callback directly
            app.screen._pending_delete_idx = 0
            app.screen._on_delete_confirmed(True)
            await pilot.pause()
            assert len(config.projects) == 1
            mock_save_config_picker.assert_called_once()
            assert table.row_count == 1

    async def test_cancel_delete_keeps_project(
        self, sample_projects, mock_save_config_picker
    ):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            app.screen._pending_delete_idx = 0
            app.screen._on_delete_confirmed(False)
            await pilot.pause()
            assert len(config.projects) == 2
            mock_save_config_picker.assert_not_called()

    async def test_d_on_empty_list_does_nothing(self):
        config = AppConfig(
            repo_path=Path("/home/user/repos/only"),
            projects=[],
        )
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            # Should not raise
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, ProjectPickerScreen)


# ---------------------------------------------------------------------------
# Cancel — Escape dismisses with None (caller decides whether to exit)
# ---------------------------------------------------------------------------


class TestProjectPickerScreenCancel:
    async def test_escape_dismisses_with_none(self, sample_projects):
        config = _make_config(sample_projects)
        screen = ProjectPickerScreen(config)
        async with ProjectPickerTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is None


# ---------------------------------------------------------------------------
# _ConfirmDeleteModal — standalone tests
# ---------------------------------------------------------------------------


class TestConfirmDeleteModal:
    async def test_yes_button_dismisses_true(self):
        class ConfirmTestApp(App[None]):
            def __init__(self):
                super().__init__()
                self.result = _UNSET

            def on_mount(self):
                self.push_screen(
                    _ConfirmDeleteModal("my-project"), callback=self._on_dismiss
                )

            def _on_dismiss(self, result):
                self.result = result

        async with ConfirmTestApp().run_test(size=(80, 20)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#yes-btn")
            await pilot.pause()
            assert app.result is True

    async def test_no_button_dismisses_false(self):
        class ConfirmTestApp(App[None]):
            def __init__(self):
                super().__init__()
                self.result = _UNSET

            def on_mount(self):
                self.push_screen(
                    _ConfirmDeleteModal("my-project"), callback=self._on_dismiss
                )

            def _on_dismiss(self, result):
                self.result = result

        async with ConfirmTestApp().run_test(size=(80, 20)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#no-btn")
            await pilot.pause()
            assert app.result is False

    async def test_escape_dismisses_false(self):
        class ConfirmTestApp(App[None]):
            def __init__(self):
                super().__init__()
                self.result = _UNSET

            def on_mount(self):
                self.push_screen(
                    _ConfirmDeleteModal("my-project"), callback=self._on_dismiss
                )

            def _on_dismiss(self, result):
                self.result = result

        async with ConfirmTestApp().run_test(size=(80, 20)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("escape")
            await pilot.pause()
            assert app.result is False

    async def test_y_key_dismisses_true(self):
        class ConfirmTestApp(App[None]):
            def __init__(self):
                super().__init__()
                self.result = _UNSET

            def on_mount(self):
                self.push_screen(
                    _ConfirmDeleteModal("my-project"), callback=self._on_dismiss
                )

            def _on_dismiss(self, result):
                self.result = result

        async with ConfirmTestApp().run_test(size=(80, 20)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("y")
            await pilot.pause()
            assert app.result is True
