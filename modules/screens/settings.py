"""SettingsScreen — edit global API keys and tokens post-onboarding."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from modules.core.config import AppConfig, save_config
from modules.core.validation import (
    validate_github_token,
    validate_linear_key,
    validate_linear_team,
)
from modules.widgets.secret_input import SecretInput

__all__ = ["SettingsScreen"]


class SettingsScreen(ModalScreen[bool]):
    """Edit global API key and token settings.

    Dismiss values: ``True`` (saved), ``False`` (cancelled).
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }
    #settings-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #settings-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }
    .settings-section-header {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }
    #settings-linear-team {
        margin-top: 1;
    }
    #settings-linear-feedback,
    #settings-github-feedback {
        height: 1;
        margin-bottom: 1;
    }
    #settings-footer {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    #settings-footer Button {
        margin: 0 1;
    }
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            yield Label("Settings", id="settings-title")
            with VerticalScroll(id="settings-body"):
                yield Label("Linear", classes="settings-section-header")
                yield SecretInput(
                    label="API Key:",
                    placeholder="lin_api_...",
                    hint="Find at linear.app/settings/api",
                    id="settings-linear-key",
                )
                yield Input(
                    placeholder="e.g. ENG",
                    id="settings-linear-team",
                )
                yield Button(
                    "Validate", id="settings-validate-linear", variant="default"
                )
                yield Static("", id="settings-linear-feedback")
                yield Label("GitHub", classes="settings-section-header")
                yield SecretInput(
                    label="Token:",
                    placeholder="ghp_...",
                    hint="Needs scopes: repo, read:user",
                    id="settings-github-token",
                )
                yield Button(
                    "Validate", id="settings-validate-github", variant="default"
                )
                yield Static("", id="settings-github-feedback")
            with Horizontal(id="settings-footer"):
                yield Button("Save", id="settings-save", variant="primary")
                yield Button("Cancel", id="settings-cancel", variant="default")

    def on_mount(self) -> None:
        if self._config.linear_api_key:
            self.query_one("#settings-linear-key", SecretInput).query_one(
                "#secret-input", Input
            ).value = self._config.linear_api_key
        if self._config.linear_team_id:
            self.query_one(
                "#settings-linear-team", Input
            ).value = self._config.linear_team_id
        if self._config.github_token:
            self.query_one("#settings-github-token", SecretInput).query_one(
                "#secret-input", Input
            ).value = self._config.github_token

    @on(Button.Pressed, "#settings-validate-linear")
    def _on_validate_linear_pressed(self, event: Button.Pressed) -> None:
        self._validate_linear()

    @on(Button.Pressed, "#settings-validate-github")
    def _on_validate_github_pressed(self, event: Button.Pressed) -> None:
        self._validate_github()

    @on(Button.Pressed, "#settings-save")
    def _on_save_pressed(self, event: Button.Pressed) -> None:
        self._do_save()

    @on(Button.Pressed, "#settings-cancel")
    def _on_cancel_pressed(self, event: Button.Pressed) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _do_save(self) -> None:
        self._config.linear_api_key = (
            self.query_one("#settings-linear-key", SecretInput).value.strip() or None
        )
        self._config.linear_team_id = (
            self.query_one("#settings-linear-team", Input).value.strip() or None
        )
        self._config.github_token = (
            self.query_one("#settings-github-token", SecretInput).value.strip() or None
        )
        save_config(self._config)
        self.dismiss(True)

    @work
    async def _validate_linear(self) -> None:
        feedback = self.query_one("#settings-linear-feedback", Static)
        api_key = self.query_one("#settings-linear-key", SecretInput).value.strip()
        team_id = self.query_one("#settings-linear-team", Input).value.strip()

        feedback.update("Validating API key...")
        ok, msg = await validate_linear_key(api_key)
        if not ok:
            feedback.update(f"[red]{msg}[/red]")
            return

        feedback.update(f"{msg}. Validating team...")
        ok2, msg2 = await validate_linear_team(api_key, team_id)
        if not ok2:
            feedback.update(f"[red]{msg2}[/red]")
            return

        feedback.update(f"[green]{msg} | {msg2}[/green]")

    @work
    async def _validate_github(self) -> None:
        feedback = self.query_one("#settings-github-feedback", Static)
        token = self.query_one("#settings-github-token", SecretInput).value.strip()

        feedback.update("Validating token...")
        ok, msg = await validate_github_token(token)
        if not ok:
            feedback.update(f"[red]{msg}[/red]")
            return

        feedback.update(f"[green]{msg}[/green]")
