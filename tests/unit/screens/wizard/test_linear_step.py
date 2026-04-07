"""Tests for LinearStepScreen."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from textual.app import App
from textual.widgets import Button, Input, Static

from modules.screens.wizard.controller import WizardController
from modules.screens.wizard.linear_step import LinearStepScreen
from modules.widgets.secret_input import SecretInput

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class LinearStepTestApp(App[None]):
    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: LinearStepScreen) -> None:
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


class TestLinearStepScreenCompose:
    async def test_renders_api_key_secret_input(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#linear-api-key", SecretInput) is not None

    async def test_renders_team_id_secret_input(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#linear-team-id", SecretInput) is not None

    async def test_renders_validate_button(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#linear-validate", Button) is not None

    async def test_next_button_disabled_initially(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#wizard-next", Button).disabled is True

    async def test_skip_button_visible(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            assert app.screen.query_one("#wizard-skip", Button).display is True


# ---------------------------------------------------------------------------
# Validation — success
# ---------------------------------------------------------------------------


class TestLinearStepValidationSuccess:
    async def test_next_enabled_after_success(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with (
            patch(
                "modules.screens.wizard.linear_step.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.wizard.linear_step.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(True, "Team: Backend"),
            ),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#linear-api-key", "lin_api_test")
                _set_secret_input(app.screen, "#linear-team-id", "ENG")
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                assert app.screen.query_one("#wizard-next", Button).disabled is False

    async def test_status_shows_success_message(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with (
            patch(
                "modules.screens.wizard.linear_step.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.wizard.linear_step.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(True, "Team: Backend"),
            ),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#linear-api-key", "lin_api_test")
                _set_secret_input(app.screen, "#linear-team-id", "ENG")
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                status_text = str(
                    app.screen.query_one("#linear-status", Static).render()
                )
                assert "Authenticated as Alice" in status_text
                assert "Team: Backend" in status_text

    async def test_data_stored_in_controller_on_success(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with (
            patch(
                "modules.screens.wizard.linear_step.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.wizard.linear_step.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(True, "Team: Backend"),
            ),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#linear-api-key", "lin_api_test")
                _set_secret_input(app.screen, "#linear-team-id", "ENG")
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                assert ctrl.data.linear_api_key == "lin_api_test"
                assert ctrl.data.linear_team_id == "ENG"


# ---------------------------------------------------------------------------
# Validation — failure (API key)
# ---------------------------------------------------------------------------


class TestLinearStepValidationKeyFailure:
    async def test_next_remains_disabled_on_key_failure(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.linear_step.validate_linear_key",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                assert app.screen.query_one("#wizard-next", Button).disabled is True

    async def test_status_shows_error_on_key_failure(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.linear_step.validate_linear_key",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                status_text = str(
                    app.screen.query_one("#linear-status", Static).render()
                )
                assert "Authentication failed" in status_text

    async def test_data_not_stored_on_key_failure(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with patch(
            "modules.screens.wizard.linear_step.validate_linear_key",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#linear-api-key", "bad_key")
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                assert ctrl.data.linear_api_key is None


# ---------------------------------------------------------------------------
# Validation — failure (team ID)
# ---------------------------------------------------------------------------


class TestLinearStepValidationTeamFailure:
    async def test_next_remains_disabled_on_team_failure(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with (
            patch(
                "modules.screens.wizard.linear_step.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.wizard.linear_step.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(False, "Team not found"),
            ),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                assert app.screen.query_one("#wizard-next", Button).disabled is True

    async def test_data_not_stored_on_team_failure(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        with (
            patch(
                "modules.screens.wizard.linear_step.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.wizard.linear_step.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(False, "Team not found"),
            ),
        ):
            async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                _set_secret_input(app.screen, "#linear-api-key", "lin_api_test")
                _set_secret_input(app.screen, "#linear-team-id", "BAD")
                await pilot.click("#linear-validate")
                await _wait_ready(pilot, app)
                assert ctrl.data.linear_api_key is None
                assert ctrl.data.linear_team_id is None


# ---------------------------------------------------------------------------
# Skip
# ---------------------------------------------------------------------------


class TestLinearStepSkip:
    async def test_skip_dismisses_with_skip(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#wizard-skip")
            await pilot.pause()
            assert app.modal_result == "skip"

    async def test_skip_leaves_data_as_none(self):
        ctrl = WizardController()
        screen = LinearStepScreen(ctrl)
        async with LinearStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#wizard-skip")
            await pilot.pause()
            assert ctrl.data.linear_api_key is None
            assert ctrl.data.linear_team_id is None
