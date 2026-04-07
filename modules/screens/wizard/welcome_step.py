"""WelcomeStepScreen — first step of the onboarding wizard."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Checkbox, Label

from .base_step import WizardStepScreen
from .controller import WizardStep

__all__ = ["WelcomeStepScreen"]


class WelcomeStepScreen(WizardStepScreen):
    """Welcome screen with app intro and integration opt-in checkboxes.

    No Back button (first step). No Skip button (not skippable).
    Unchecking a checkbox disables the corresponding wizard step.
    """

    skippable = False

    def compose_step_content(self) -> ComposeResult:
        yield Label(
            "Welcome to tt-tmux\n\n"
            "Manage Git worktrees with tmux — fast, keyboard-driven,\n"
            "and integrated with your issue tracker and GitHub.\n\n"
            "Select which integrations you'd like to configure:"
        )
        yield Checkbox("Set up Linear integration", value=True, id="welcome-linear-cb")
        yield Checkbox("Set up GitHub integration", value=True, id="welcome-github-cb")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "welcome-linear-cb":
            if event.value:
                self._controller.enable(WizardStep.LINEAR)
            else:
                self._controller.disable(WizardStep.LINEAR)
        elif event.checkbox.id == "welcome-github-cb":
            if event.value:
                self._controller.enable(WizardStep.GITHUB)
            else:
                self._controller.disable(WizardStep.GITHUB)
