"""Tests for ProjectStepScreen."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from textual.app import App
from textual.containers import Vertical
from textual.widgets import Button, Input, Static

from modules.screens.wizard.controller import WizardController
from modules.screens.wizard.project_step import ProjectStepScreen
from modules.widgets.directory_input import DirectoryInput

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class ProjectStepTestApp(App[None]):
    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: ProjectStepScreen) -> None:
        super().__init__()
        self._screen = screen
        self.modal_result: Any = _UNSET

    def on_mount(self) -> None:
        self.push_screen(self._screen, callback=self._on_dismiss)

    def _on_dismiss(self, result: str) -> None:
        self.modal_result = result


async def _wait_ready(pilot, app) -> None:
    await pilot.pause()
    await pilot.pause()
    await app.workers.wait_for_complete()


def _set_dir_input(screen, value: str) -> None:
    screen.query_one("#project-dir-input", DirectoryInput).query_one(
        "#dir-input", Input
    ).value = value


# ---------------------------------------------------------------------------
# Compose / initial state
# ---------------------------------------------------------------------------


class TestProjectStepScreenCompose:
    async def test_renders_directory_input(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert (
                pilot.app.screen.query_one("#project-dir-input", DirectoryInput)
                is not None
            )

    async def test_renders_validate_button(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#project-validate", Button) is not None

    async def test_renders_status_widget(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#project-status", Static) is not None

    async def test_next_button_disabled_initially(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#wizard-next", Button).disabled is True

    async def test_github_repo_container_hidden_when_no_token(self):
        ctrl = WizardController()
        ctrl.data.github_token = None
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            container = pilot.app.screen.query_one(
                "#project-github-repo-container", Vertical
            )
            assert container.display is False

    async def test_github_repo_container_visible_when_token_set(self):
        ctrl = WizardController()
        ctrl.data.github_token = "ghp_test"
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            container = pilot.app.screen.query_one(
                "#project-github-repo-container", Vertical
            )
            assert container.display is True


# ---------------------------------------------------------------------------
# Validation — failure
# ---------------------------------------------------------------------------


class TestProjectStepValidationFailure:
    async def test_empty_path_shows_error(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            _set_dir_input(pilot.app.screen, "")
            await pilot.click("#project-validate")
            await _wait_ready(pilot, pilot.app)
            status_text = str(
                pilot.app.screen.query_one("#project-status", Static).render()
            )
            assert (
                "enter a path" in status_text.lower()
                or "invalid" in status_text.lower()
                or "exist" in status_text.lower()
            )

    async def test_nonexistent_path_shows_error(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            _set_dir_input(pilot.app.screen, "/definitely/does/not/exist/xyz123abc")
            await pilot.click("#project-validate")
            await _wait_ready(pilot, pilot.app)
            status_text = str(
                pilot.app.screen.query_one("#project-status", Static).render()
            )
            assert "not exist" in status_text or "directory" in status_text

    async def test_not_git_repo_shows_error(self, tmp_path):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=False,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                status_text = str(
                    pilot.app.screen.query_one("#project-status", Static).render()
                )
                assert "git" in status_text.lower()

    async def test_bad_github_repo_format_shows_error(self, tmp_path):
        ctrl = WizardController()
        ctrl.data.github_token = "ghp_test"
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                pilot.app.screen.query_one(
                    "#project-github-repo", Input
                ).value = "notaslash"
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                status_text = str(
                    pilot.app.screen.query_one("#project-status", Static).render()
                )
                assert "owner/repo" in status_text

    async def test_next_remains_disabled_on_failure(self):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            _set_dir_input(pilot.app.screen, "/nonexistent/path")
            await pilot.click("#project-validate")
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#wizard-next", Button).disabled is True


# ---------------------------------------------------------------------------
# Validation — success
# ---------------------------------------------------------------------------


class TestProjectStepValidationSuccess:
    async def test_next_enabled_after_success(self, tmp_path):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                assert (
                    pilot.app.screen.query_one("#wizard-next", Button).disabled is False
                )

    async def test_project_path_stored_in_controller(self, tmp_path):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                assert ctrl.data.project_path == tmp_path.resolve()

    async def test_github_repo_stored_when_token_set(self, tmp_path):
        ctrl = WizardController()
        ctrl.data.github_token = "ghp_test"
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                pilot.app.screen.query_one(
                    "#project-github-repo", Input
                ).value = "owner/repo"
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                assert ctrl.data.github_repo == "owner/repo"

    async def test_github_repo_none_when_no_token(self, tmp_path):
        ctrl = WizardController()
        ctrl.data.github_token = None
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                assert ctrl.data.github_repo is None

    async def test_status_shows_success_message(self, tmp_path):
        ctrl = WizardController()
        screen = ProjectStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.project_step.is_git_repo",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with ProjectStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                _set_dir_input(pilot.app.screen, str(tmp_path))
                await pilot.click("#project-validate")
                await _wait_ready(pilot, pilot.app)
                status_text = str(
                    pilot.app.screen.query_one("#project-status", Static).render()
                )
                assert "valid" in status_text.lower()
