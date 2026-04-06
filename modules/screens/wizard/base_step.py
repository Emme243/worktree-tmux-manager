"""Abstract base class for wizard step screens."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from .controller import WizardController

__all__ = ["WizardStepScreen"]


class WizardStepScreen(ModalScreen[str]):
    """Abstract base for wizard step screens.

    Subclasses implement ``compose_step_content()`` and may set
    ``skippable = True`` to show the Skip button.

    Dismiss values: ``"next"``, ``"back"``, ``"skip"``, ``"cancel"``.
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    DEFAULT_CSS = """
    WizardStepScreen {
        align: center middle;
    }
    #wizard-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #wizard-progress {
        color: $text-muted;
        text-align: right;
        height: 1;
        margin-bottom: 1;
    }
    #wizard-body {
        height: auto;
        max-height: 20;
    }
    #wizard-footer {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    #wizard-footer Button {
        margin: 0 1;
    }
    """

    skippable: bool = False

    def __init__(self, controller: WizardController) -> None:
        super().__init__()
        self._controller = controller

    def compose(self) -> ComposeResult:
        next_label = "Finish" if self._controller.is_last else "Next"
        with Vertical(id="wizard-dialog"):
            yield Static(self._controller.progress, id="wizard-progress")
            with VerticalScroll(id="wizard-body"):
                yield from self.compose_step_content()
            with Horizontal(id="wizard-footer"):
                yield Button("Back", id="wizard-back", variant="default")
                yield Button("Skip", id="wizard-skip", variant="default")
                yield Button(next_label, id="wizard-next", variant="primary")

    def compose_step_content(self) -> ComposeResult:
        """Yield widgets for the step-specific body area.

        Subclasses must override this method.
        """
        raise NotImplementedError

    def on_mount(self) -> None:
        self.query_one("#wizard-back").display = not self._controller.is_first
        self.query_one("#wizard-skip").display = self.skippable

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "wizard-next":
                self.dismiss("next")
            case "wizard-back":
                self.dismiss("back")
            case "wizard-skip":
                self.dismiss("skip")

    def action_cancel(self) -> None:
        self.dismiss("cancel")
