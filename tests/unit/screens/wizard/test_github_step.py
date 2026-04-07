"""Tests for GithubStepScreen."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from textual.app import App
from textual.widgets import Button, Input, Static

from modules.screens.wizard.controller import WizardController
from modules.screens.wizard.github_step import GithubStepScreen
from modules.widgets.secret_input import SecretInput

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class GithubStepTestApp(App[None]):
    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: GithubStepScreen) -> None:
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


def _set_secret_input(screen, outer_id: str, value: str) -> None:
    """Set the inner Input value of a SecretInput by its outer id."""
    screen.query_one(outer_id, SecretInput).query_one(
        "#secret-input", Input
    ).value = value


# ---------------------------------------------------------------------------
# Compose / initial state
# ---------------------------------------------------------------------------


class TestGithubStepScreenCompose:
    async def test_renders_token_secret_input(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#github-token", SecretInput) is not None

    async def test_renders_validate_button(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#github-validate", Button) is not None

    async def test_next_button_disabled_initially(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#wizard-next", Button).disabled is True

    async def test_skip_button_visible(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#wizard-skip", Button).display is True


# ---------------------------------------------------------------------------
# Validation — success
# ---------------------------------------------------------------------------


class TestGithubStepValidationSuccess:
    async def test_next_enabled_after_success(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.github_step.validate_github_token",
            new_callable=AsyncMock,
            return_value=(True, "Authenticated as octocat"),
        ):
            async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#github-token", "ghp_test")
                await pilot.click("#github-validate")
                await _wait_ready(pilot, app)
                assert app.screen.query_one("#wizard-next", Button).disabled is False

    async def test_status_shows_success_message(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.github_step.validate_github_token",
            new_callable=AsyncMock,
            return_value=(True, "Authenticated as octocat"),
        ):
            async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#github-token", "ghp_test")
                await pilot.click("#github-validate")
                await _wait_ready(pilot, app)
                status_text = str(
                    app.screen.query_one("#github-status", Static).render()
                )
                assert "Authenticated as octocat" in status_text

    async def test_token_stored_in_controller_on_success(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.github_step.validate_github_token",
            new_callable=AsyncMock,
            return_value=(True, "Authenticated as octocat"),
        ):
            async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#github-token", "ghp_test")
                await pilot.click("#github-validate")
                await _wait_ready(pilot, app)
                assert ctrl.data.github_token == "ghp_test"


# ---------------------------------------------------------------------------
# Validation — failure
# ---------------------------------------------------------------------------


class TestGithubStepValidationFailure:
    async def test_next_remains_disabled_on_failure(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.github_step.validate_github_token",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                await pilot.click("#github-validate")
                await _wait_ready(pilot, app)
                assert app.screen.query_one("#wizard-next", Button).disabled is True

    async def test_status_shows_error_on_failure(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.github_step.validate_github_token",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                await pilot.click("#github-validate")
                await _wait_ready(pilot, app)
                status_text = str(
                    app.screen.query_one("#github-status", Static).render()
                )
                assert "Authentication failed" in status_text

    async def test_token_not_stored_on_failure(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.github_step.validate_github_token",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#github-token", "bad_token")
                await pilot.click("#github-validate")
                await _wait_ready(pilot, app)
                assert ctrl.data.github_token is None


# ---------------------------------------------------------------------------
# Skip
# ---------------------------------------------------------------------------


class TestGithubStepSkip:
    async def test_skip_dismisses_with_skip(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#wizard-skip")
            await pilot.pause()
            assert app.modal_result == "skip"

    async def test_skip_leaves_token_as_none(self):
        ctrl = WizardController()
        screen = GithubStepScreen(ctrl)
        async with GithubStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#wizard-skip")
            await pilot.pause()
            assert ctrl.data.github_token is None
