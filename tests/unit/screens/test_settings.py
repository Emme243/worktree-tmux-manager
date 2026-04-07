"""Tests for modules.screens.settings — SettingsScreen."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Input, Static

from modules.core.config import AppConfig, ProjectConfig
from modules.screens.settings import SettingsScreen
from modules.widgets.secret_input import SecretInput

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class SettingsTestApp(App[None]):
    """Minimal host app that pushes SettingsScreen and captures its result."""

    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: SettingsScreen) -> None:
        super().__init__()
        self._screen = screen
        self.modal_result: Any = _UNSET

    def on_mount(self) -> None:
        self.push_screen(self._screen, callback=self._on_dismiss)

    def _on_dismiss(self, result: bool) -> None:
        self.modal_result = result


async def _wait_ready(pilot, app) -> None:
    await pilot.pause()
    await pilot.pause()
    await app.workers.wait_for_complete()


def _set_secret_input(screen, outer_id: str, value: str) -> None:
    """Drill into SecretInput's inner Input and set its value directly."""
    screen.query_one(outer_id, SecretInput).query_one(
        "#secret-input", Input
    ).value = value


def _get_secret_input_value(screen, outer_id: str) -> str:
    return (
        screen.query_one(outer_id, SecretInput).query_one("#secret-input", Input).value
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_config() -> AppConfig:
    return AppConfig(
        repo_path=Path("/home/user/repos/project"),
        linear_api_key="lin_api_existing",
        linear_team_id="ENG",
        github_token="ghp_existing",
        projects=[ProjectConfig(path=Path("/home/user/repos/project"))],
    )


@pytest.fixture
def empty_config() -> AppConfig:
    return AppConfig(
        repo_path=Path("/home/user/repos/project"),
        projects=[ProjectConfig(path=Path("/home/user/repos/project"))],
    )


@pytest.fixture
def mock_save_config_settings():
    with patch("modules.screens.settings.save_config") as mock:
        yield mock


# ---------------------------------------------------------------------------
# Compose / Pre-populate
# ---------------------------------------------------------------------------


class TestSettingsScreenCompose:
    async def test_renders_title(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            from textual.widgets import Label

            label = pilot.app.screen.query_one("#settings-title", Label)
            assert "Settings" in label.render().plain

    async def test_renders_linear_key_input(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            widget = pilot.app.screen.query_one("#settings-linear-key", SecretInput)
            assert widget is not None

    async def test_renders_linear_team_input(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            widget = pilot.app.screen.query_one("#settings-linear-team", Input)
            assert widget is not None

    async def test_renders_validate_linear_button(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            btn = pilot.app.screen.query_one("#settings-validate-linear", Button)
            assert btn is not None

    async def test_renders_linear_feedback_empty(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            fb = pilot.app.screen.query_one("#settings-linear-feedback", Static)
            assert fb.render().plain.strip() == ""

    async def test_renders_github_token_input(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            widget = pilot.app.screen.query_one("#settings-github-token", SecretInput)
            assert widget is not None

    async def test_renders_validate_github_button(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            btn = pilot.app.screen.query_one("#settings-validate-github", Button)
            assert btn is not None

    async def test_renders_github_feedback_empty(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            fb = pilot.app.screen.query_one("#settings-github-feedback", Static)
            assert fb.render().plain.strip() == ""

    async def test_renders_save_button(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            btn = pilot.app.screen.query_one("#settings-save", Button)
            assert btn is not None

    async def test_renders_cancel_button(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            btn = pilot.app.screen.query_one("#settings-cancel", Button)
            assert btn is not None

    async def test_prepopulates_linear_key(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            value = _get_secret_input_value(pilot.app.screen, "#settings-linear-key")
            assert value == "lin_api_existing"

    async def test_prepopulates_linear_team(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            value = pilot.app.screen.query_one("#settings-linear-team", Input).value
            assert value == "ENG"

    async def test_prepopulates_github_token(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            value = _get_secret_input_value(pilot.app.screen, "#settings-github-token")
            assert value == "ghp_existing"

    async def test_empty_config_inputs_are_empty(self, empty_config):
        async with SettingsTestApp(SettingsScreen(empty_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert (
                _get_secret_input_value(pilot.app.screen, "#settings-linear-key") == ""
            )
            assert (
                pilot.app.screen.query_one("#settings-linear-team", Input).value == ""
            )
            assert (
                _get_secret_input_value(pilot.app.screen, "#settings-github-token")
                == ""
            )


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


class TestSettingsScreenSave:
    async def test_save_calls_save_config(
        self, mock_save_config_settings, sample_config
    ):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            await pilot.click("#settings-save")
            await _wait_ready(pilot, pilot.app)
            mock_save_config_settings.assert_called_once()

    async def test_save_passes_updated_linear_team(
        self, mock_save_config_settings, sample_config
    ):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            pilot.app.screen.query_one("#settings-linear-team", Input).value = "NEWTEAM"
            await pilot.click("#settings-save")
            await _wait_ready(pilot, pilot.app)
            saved_config: AppConfig = mock_save_config_settings.call_args[0][0]
            assert saved_config.linear_team_id == "NEWTEAM"

    async def test_save_dismisses_with_true(
        self, mock_save_config_settings, sample_config
    ):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#settings-save")
            await _wait_ready(pilot, app)
            assert app.modal_result is True

    async def test_save_empty_fields_stored_as_none(
        self, mock_save_config_settings, empty_config
    ):
        async with SettingsTestApp(SettingsScreen(empty_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            await pilot.click("#settings-save")
            await _wait_ready(pilot, pilot.app)
            saved_config: AppConfig = mock_save_config_settings.call_args[0][0]
            assert saved_config.linear_api_key is None
            assert saved_config.linear_team_id is None
            assert saved_config.github_token is None


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


class TestSettingsScreenCancel:
    async def test_cancel_button_dismisses_with_false(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#settings-cancel")
            await pilot.pause()
            assert app.modal_result is False

    async def test_escape_dismisses_with_false(self, sample_config):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is False

    async def test_cancel_does_not_call_save_config(
        self, mock_save_config_settings, sample_config
    ):
        async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
            size=(100, 40)
        ) as pilot:
            await _wait_ready(pilot, pilot.app)
            await pilot.click("#settings-cancel")
            await pilot.pause()
            mock_save_config_settings.assert_not_called()


# ---------------------------------------------------------------------------
# Linear validation
# ---------------------------------------------------------------------------


class TestSettingsLinearValidation:
    async def test_success_shows_green_feedback(self, sample_config):
        with (
            patch(
                "modules.screens.settings.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.settings.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(True, "Team: Backend"),
            ),
        ):
            async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
                size=(100, 40)
            ) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#settings-validate-linear")
                await _wait_ready(pilot, pilot.app)
                fb = pilot.app.screen.query_one("#settings-linear-feedback", Static)
                text = str(fb.render())
                assert "Authenticated as Alice" in text
                assert "Team: Backend" in text

    async def test_key_failure_shows_red_feedback(self, sample_config):
        with patch(
            "modules.screens.settings.validate_linear_key",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
                size=(100, 40)
            ) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#settings-validate-linear")
                await _wait_ready(pilot, pilot.app)
                fb = pilot.app.screen.query_one("#settings-linear-feedback", Static)
                text = str(fb.render())
                assert "Authentication failed" in text

    async def test_team_failure_shows_red_feedback(self, sample_config):
        with (
            patch(
                "modules.screens.settings.validate_linear_key",
                new_callable=AsyncMock,
                return_value=(True, "Authenticated as Alice"),
            ),
            patch(
                "modules.screens.settings.validate_linear_team",
                new_callable=AsyncMock,
                return_value=(False, "Team not found"),
            ),
        ):
            async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
                size=(100, 40)
            ) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#settings-validate-linear")
                await _wait_ready(pilot, pilot.app)
                fb = pilot.app.screen.query_one("#settings-linear-feedback", Static)
                text = str(fb.render())
                assert "Team not found" in text


# ---------------------------------------------------------------------------
# GitHub validation
# ---------------------------------------------------------------------------


class TestSettingsGitHubValidation:
    async def test_success_shows_green_feedback(self, sample_config):
        with patch(
            "modules.screens.settings.validate_github_token",
            new_callable=AsyncMock,
            return_value=(True, "Authenticated as alice"),
        ):
            async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
                size=(100, 60)
            ) as pilot:
                await _wait_ready(pilot, pilot.app)
                pilot.app.screen.query_one("#settings-validate-github", Button).press()
                await _wait_ready(pilot, pilot.app)
                fb = pilot.app.screen.query_one("#settings-github-feedback", Static)
                text = str(fb.render())
                assert "Authenticated as alice" in text

    async def test_failure_shows_red_feedback(self, sample_config):
        with patch(
            "modules.screens.settings.validate_github_token",
            new_callable=AsyncMock,
            return_value=(False, "Authentication failed"),
        ):
            async with SettingsTestApp(SettingsScreen(sample_config)).run_test(
                size=(100, 60)
            ) as pilot:
                await _wait_ready(pilot, pilot.app)
                pilot.app.screen.query_one("#settings-validate-github", Button).press()
                await _wait_ready(pilot, pilot.app)
                fb = pilot.app.screen.query_one("#settings-github-feedback", Static)
                text = str(fb.render())
                assert "Authentication failed" in text
