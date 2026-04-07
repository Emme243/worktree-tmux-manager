"""Tests for WelcomeStepScreen."""

from __future__ import annotations

from typing import Any

from textual.app import App
from textual.widgets import Button, Checkbox

from modules.screens.wizard.controller import WizardController, WizardStep
from modules.screens.wizard.welcome_step import WelcomeStepScreen

# ---------------------------------------------------------------------------
# Test host app
# ---------------------------------------------------------------------------

_UNSET = object()


class WelcomeStepTestApp(App[None]):
    CSS = "Screen { align: center middle; }"

    def __init__(self, screen: WelcomeStepScreen) -> None:
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


# ---------------------------------------------------------------------------
# Compose / initial state
# ---------------------------------------------------------------------------


class TestWelcomeStepScreenCompose:
    async def test_linear_checkbox_checked_by_default(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            cb = app.screen.query_one("#welcome-linear-cb", Checkbox)
            assert cb.value is True

    async def test_github_checkbox_checked_by_default(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            cb = app.screen.query_one("#welcome-github-cb", Checkbox)
            assert cb.value is True

    async def test_no_back_button_visible(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            back = app.screen.query_one("#wizard-back", Button)
            assert back.display is False

    async def test_skip_button_not_visible(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            skip = app.screen.query_one("#wizard-skip", Button)
            assert skip.display is False

    async def test_next_button_present_and_enabled(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            nxt = app.screen.query_one("#wizard-next", Button)
            assert nxt is not None
            assert nxt.disabled is False


# ---------------------------------------------------------------------------
# Checkbox → controller interaction
# ---------------------------------------------------------------------------


class TestWelcomeStepCheckboxes:
    async def test_uncheck_linear_disables_linear_step(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            cb = app.screen.query_one("#welcome-linear-cb", Checkbox)
            cb.value = False
            await pilot.pause()
            assert ctrl.is_enabled(WizardStep.LINEAR) is False

    async def test_uncheck_github_disables_github_step(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            cb = app.screen.query_one("#welcome-github-cb", Checkbox)
            cb.value = False
            await pilot.pause()
            assert ctrl.is_enabled(WizardStep.GITHUB) is False

    async def test_recheck_linear_reenables_step(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            cb = app.screen.query_one("#welcome-linear-cb", Checkbox)
            cb.value = False
            await pilot.pause()
            cb.value = True
            await pilot.pause()
            assert ctrl.is_enabled(WizardStep.LINEAR) is True

    async def test_recheck_github_reenables_step(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            cb = app.screen.query_one("#welcome-github-cb", Checkbox)
            cb.value = False
            await pilot.pause()
            cb.value = True
            await pilot.pause()
            assert ctrl.is_enabled(WizardStep.GITHUB) is True

    async def test_next_dismisses_with_next(self):
        ctrl = WizardController()
        screen = WelcomeStepScreen(ctrl)
        async with WelcomeStepTestApp(screen).run_test(size=(100, 40)) as pilot:
            app = pilot.app
            await _wait_ready(pilot, app)
            await pilot.click("#wizard-next")
            await pilot.pause()
            assert app.modal_result == "next"
