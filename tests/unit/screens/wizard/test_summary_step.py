"""Tests for SummaryStepScreen."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from textual.app import App
from textual.widgets import Button, Static

from modules.core.config import AppConfig
from modules.screens.wizard.controller import WizardController, WizardData
from modules.screens.wizard.summary_step import SummaryStepScreen

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class SummaryStepTestApp(App[None]):
    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: SummaryStepScreen) -> None:
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


def _make_controller(
    project_path: Path | None = Path("/some/project"),
    linear_api_key: str | None = None,
    linear_team_id: str | None = None,
    github_token: str | None = None,
    github_repo: str | None = None,
) -> WizardController:
    ctrl = WizardController()
    ctrl.data = WizardData(
        project_path=project_path,
        linear_api_key=linear_api_key,
        linear_team_id=linear_team_id,
        github_token=github_token,
        github_repo=github_repo,
    )
    return ctrl


# ---------------------------------------------------------------------------
# Compose / initial state
# ---------------------------------------------------------------------------


class TestSummaryStepScreenCompose:
    async def test_renders_summary_text(self):
        ctrl = _make_controller()
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#summary-text", Static) is not None

    async def test_renders_finish_button(self):
        ctrl = _make_controller()
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#summary-finish", Button) is not None

    async def test_wizard_next_hidden(self):
        ctrl = _make_controller()
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            assert pilot.app.screen.query_one("#wizard-next", Button).display is False

    async def test_shows_project_path_in_summary(self):
        ctrl = _make_controller(project_path=Path("/repos/myproject"))
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            text = str(pilot.app.screen.query_one("#summary-text", Static).render())
            assert "/repos/myproject" in text

    async def test_shows_linear_configured_when_set(self):
        ctrl = _make_controller(linear_api_key="lin_api_abc123", linear_team_id="ENG")
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            text = str(pilot.app.screen.query_one("#summary-text", Static).render())
            assert "Linear: configured" in text

    async def test_shows_linear_skipped_when_none(self):
        ctrl = _make_controller(linear_api_key=None)
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            text = str(pilot.app.screen.query_one("#summary-text", Static).render())
            assert "Linear: skipped" in text

    async def test_shows_github_configured_when_token_set(self):
        ctrl = _make_controller(github_token="ghp_test")
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            text = str(pilot.app.screen.query_one("#summary-text", Static).render())
            assert "GitHub: token set" in text

    async def test_shows_github_skipped_when_none(self):
        ctrl = _make_controller(github_token=None)
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            text = str(pilot.app.screen.query_one("#summary-text", Static).render())
            assert "GitHub: skipped" in text

    async def test_shows_github_repo_when_set(self):
        ctrl = _make_controller(github_token="ghp_test", github_repo="org/proj")
        screen = SummaryStepScreen(ctrl)
        async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, pilot.app)
            text = str(pilot.app.screen.query_one("#summary-text", Static).render())
            assert "org/proj" in text


# ---------------------------------------------------------------------------
# Finish button
# ---------------------------------------------------------------------------


class TestSummaryStepFinish:
    async def test_finish_calls_save_config(self):
        ctrl = _make_controller(project_path=Path("/repos/alpha"))
        screen = SummaryStepScreen(ctrl)
        mock_save = MagicMock()
        with patch("modules.screens.wizard.summary_step.save_config", mock_save):
            async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#summary-finish")
                await _wait_ready(pilot, pilot.app)
                mock_save.assert_called_once()

    async def test_finish_dismisses_with_next(self):
        ctrl = _make_controller(project_path=Path("/repos/alpha"))
        screen = SummaryStepScreen(ctrl)
        with patch("modules.screens.wizard.summary_step.save_config", MagicMock()):
            async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                app = pilot.app
                await _wait_ready(pilot, app)
                await pilot.click("#summary-finish")
                await _wait_ready(pilot, app)
                assert app.modal_result == "next"

    async def test_save_config_receives_correct_repo_path(self):
        ctrl = _make_controller(project_path=Path("/repos/alpha"))
        screen = SummaryStepScreen(ctrl)
        captured: list[AppConfig] = []

        def _capture(cfg, *args, **kwargs):
            captured.append(cfg)

        with patch(
            "modules.screens.wizard.summary_step.save_config", side_effect=_capture
        ):
            async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#summary-finish")
                await _wait_ready(pilot, pilot.app)
                assert captured[0].repo_path == Path("/repos/alpha")

    async def test_save_config_includes_api_keys(self):
        ctrl = _make_controller(
            project_path=Path("/repos/alpha"),
            linear_api_key="lin_abc",
            linear_team_id="ENG",
            github_token="ghp_xyz",
        )
        screen = SummaryStepScreen(ctrl)
        captured: list[AppConfig] = []

        def _capture(cfg, *args, **kwargs):
            captured.append(cfg)

        with patch(
            "modules.screens.wizard.summary_step.save_config", side_effect=_capture
        ):
            async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#summary-finish")
                await _wait_ready(pilot, pilot.app)
                cfg = captured[0]
                assert cfg.linear_api_key == "lin_abc"
                assert cfg.linear_team_id == "ENG"
                assert cfg.github_token == "ghp_xyz"

    async def test_save_config_projects_list_has_one_entry(self):
        ctrl = _make_controller(project_path=Path("/repos/alpha"))
        screen = SummaryStepScreen(ctrl)
        captured: list[AppConfig] = []

        def _capture(cfg, *args, **kwargs):
            captured.append(cfg)

        with patch(
            "modules.screens.wizard.summary_step.save_config", side_effect=_capture
        ):
            async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#summary-finish")
                await _wait_ready(pilot, pilot.app)
                assert len(captured[0].projects) == 1

    async def test_project_config_github_repo_set_correctly(self):
        ctrl = _make_controller(
            project_path=Path("/repos/alpha"),
            github_token="ghp_xyz",
            github_repo="org/proj",
        )
        screen = SummaryStepScreen(ctrl)
        captured: list[AppConfig] = []

        def _capture(cfg, *args, **kwargs):
            captured.append(cfg)

        with patch(
            "modules.screens.wizard.summary_step.save_config", side_effect=_capture
        ):
            async with SummaryStepTestApp(screen).run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, pilot.app)
                await pilot.click("#summary-finish")
                await _wait_ready(pilot, pilot.app)
                assert captured[0].projects[0].github_repo == "org/proj"
