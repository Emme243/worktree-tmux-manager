"""SecretInput — Label + masked Input + hint + Show/Hide toggle composed widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static


class SecretInput(Widget):
    """Label + password Input + hint text + Show/Hide toggle for API key entry."""

    DEFAULT_CSS = "SecretInput { height: auto; }"

    def __init__(
        self,
        label: str = "Secret:",
        placeholder: str = "",
        hint: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._label = label
        self._placeholder = placeholder
        self._hint = hint

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Input(
            placeholder=self._placeholder,
            password=True,
            id="secret-input",
        )
        hint_widget = Static(self._hint, id="secret-hint")
        if not self._hint:
            hint_widget.display = False
        yield hint_widget
        yield Button("Show", id="secret-toggle", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "secret-toggle":
            return
        inp = self.query_one("#secret-input", Input)
        inp.password = not inp.password
        event.button.label = "Show" if inp.password else "Hide"

    @property
    def value(self) -> str:
        """Current text in the input (never masked in code, only in display)."""
        return self.query_one("#secret-input", Input).value
