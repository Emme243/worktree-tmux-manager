"""Tests for modules.screens.project_setup — ProjectSetupScreen."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Input, Label, Static

from modules.core.config import AppConfig
from modules.screens.project_setup import ProjectSetupScreen
from modules.widgets.directory_input import DirectoryInput

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class ProjectSetupTestApp(App[None]):
    """Minimal host app that pushes ProjectSetupScreen and captures its result."""

    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: ProjectSetupScreen) -> None:
        super().__init__()
        self._screen = screen
        self.modal_result: Any = _UNSET

    def on_mount(self) -> None:
        self.push_screen(self._screen, callback=self._on_dismiss)

    def _on_dismiss(self, result: Path | None) -> None:
        self.modal_result = result


async def _wait_ready(pilot, app) -> None:
    await pilot.pause()
    await pilot.pause()
    await app.workers.wait_for_complete()


# ---------------------------------------------------------------------------
# Compose / Init
# ---------------------------------------------------------------------------


class TestProjectSetupScreenCompose:
    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_renders_title(self, mode):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            title = app.screen.query_one("#setup-title", Label)
            assert title is not None
            assert title.render().plain.strip() != ""

    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_first_run_title_text(self, mode):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            title = app.screen.query_one("#setup-title", Label)
            text = title.render().plain
            if mode == "first_run":
                assert "Welcome" in text
            else:
                assert "Add Project" in text

    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_renders_directory_input(self, mode):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            widget = app.screen.query_one(DirectoryInput)
            assert widget is not None

    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_renders_error_static_initially_empty(self, mode):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            error = app.screen.query_one("#setup-error", Static)
            assert error.render().plain.strip() == ""

    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_renders_confirm_button(self, mode):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            btn = app.screen.query_one("#confirm-btn", Button)
            assert "Confirm" in str(btn.label)


# ---------------------------------------------------------------------------
# Validation — inline error, no dismiss
# ---------------------------------------------------------------------------


class TestProjectSetupScreenValidation:
    async def test_empty_path_shows_inline_error(
        self, mock_save_config, mock_is_git_repo
    ):
        screen = ProjectSetupScreen(mode="add")
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            # Leave path empty and click Confirm
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            error = app.screen.query_one("#setup-error", Static)
            assert error.render().plain.strip() != ""
            assert app.modal_result is _UNSET

    async def test_nonexistent_path_shows_inline_error(
        self, mock_save_config, mock_is_git_repo
    ):
        screen = ProjectSetupScreen(mode="add")
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            app.screen.query_one("#dir-input", Input).value = "/does/not/exist/anywhere"
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            error = app.screen.query_one("#setup-error", Static)
            assert error.render().plain.strip() != ""
            assert app.modal_result is _UNSET

    async def test_non_git_dir_shows_inline_error(self, mock_save_config, non_git_dir):
        with patch(
            "modules.screens.project_setup.is_git_repo",
            new_callable=AsyncMock,
            return_value=False,
        ):
            screen = ProjectSetupScreen(mode="add")
            async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                app.screen.query_one("#dir-input", Input).value = str(non_git_dir)
                await pilot.click("#confirm-btn")
                await pilot.pause()
                await app.workers.wait_for_complete()
                error = app.screen.query_one("#setup-error", Static)
                assert error.render().plain.strip() != ""
                assert app.modal_result is _UNSET

    async def test_error_cleared_on_next_valid_attempt(
        self, mock_save_config, mock_is_git_repo, git_repo_dir
    ):
        screen = ProjectSetupScreen(mode="add")
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            # First attempt: invalid path
            app.screen.query_one("#dir-input", Input).value = "/does/not/exist"
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert (
                app.screen.query_one("#setup-error", Static).render().plain.strip()
                != ""
            )
            # Second attempt: valid path — call _do_confirm() directly to avoid
            # click-timing races between sequential @work workers.
            app.screen.query_one("#dir-input", Input).value = str(git_repo_dir)
            app.screen._do_confirm()
            await pilot.pause()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
            # Screen dismissed with a valid path
            assert isinstance(app.modal_result, Path)


# ---------------------------------------------------------------------------
# Cancel — mode-dependent Escape behaviour
# ---------------------------------------------------------------------------


class TestProjectSetupScreenCancel:
    async def test_escape_add_mode_dismisses_none(self):
        screen = ProjectSetupScreen(mode="add")
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is None

    async def test_escape_first_run_mode_exits_app(self):
        screen = ProjectSetupScreen(mode="first_run")
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("escape")
            await pilot.pause()
            assert app.return_code is not None


# ---------------------------------------------------------------------------
# Success — save + dismiss
# ---------------------------------------------------------------------------


class TestProjectSetupScreenSuccess:
    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_success_dismisses_with_path(
        self, mock_save_config, mock_is_git_repo, git_repo_dir, mode
    ):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            app.screen.query_one("#dir-input", Input).value = str(git_repo_dir)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert isinstance(app.modal_result, Path)
            assert app.modal_result == git_repo_dir.resolve()

    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_success_calls_save_config(
        self, mock_save_config, mock_is_git_repo, git_repo_dir, mode
    ):
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            app.screen.query_one("#dir-input", Input).value = str(git_repo_dir)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_save_config.assert_called_once()
            call_config: AppConfig = mock_save_config.call_args[0][0]
            assert isinstance(call_config, AppConfig)
            assert call_config.repo_path == git_repo_dir.resolve()

    @pytest.mark.parametrize("mode", ["first_run", "add"])
    async def test_enter_key_triggers_confirm(
        self, mock_save_config, mock_is_git_repo, git_repo_dir, mode
    ):
        """Verify on_input_submitted fires _do_confirm by posting Input.Submitted directly.

        We post the message rather than pilot.press("enter") because the
        AutoComplete widget intercepts Enter when its dropdown is open.
        """
        screen = ProjectSetupScreen(mode=mode)
        async with ProjectSetupTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            inner_input = app.screen.query_one("#dir-input", Input)
            inner_input.value = str(git_repo_dir)
            # Post Input.Submitted to simulate Enter — bypasses autocomplete interception
            # post_message is synchronous in Textual (returns bool, not coroutine)
            app.screen.post_message(Input.Submitted(inner_input, inner_input.value))
            await pilot.pause()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.modal_result, Path)
