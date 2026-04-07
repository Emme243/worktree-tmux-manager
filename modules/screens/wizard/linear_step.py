"""LinearStepScreen — Linear API key and team ID setup step."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.widgets import Button, Label, Static

from modules.core.validation import validate_linear_key, validate_linear_team
from modules.widgets.secret_input import SecretInput

from .base_step import WizardStepScreen

__all__ = ["LinearStepScreen"]


class LinearStepScreen(WizardStepScreen):
    """Collect Linear API key and team ID with inline validation.

    Next is disabled until validation passes. The step is skippable —
    skipping leaves ``controller.data.linear_api_key`` as ``None``.
    """

    skippable = True

    def compose_step_content(self) -> ComposeResult:
        yield Label("Configure Linear Integration")
        yield SecretInput(
            label="Linear API Key:",
            placeholder="lin_api_...",
            hint="Find at linear.app/settings/api",
            id="linear-api-key",
        )
        yield SecretInput(
            label="Linear Team ID:",
            placeholder="e.g. ENG",
            hint="Settings → Members → copy the team ID",
            id="linear-team-id",
        )
        yield Button("Validate", id="linear-validate", variant="default")
        yield Static("", id="linear-status")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#wizard-next", Button).disabled = True

    @on(Button.Pressed, "#linear-validate")
    def _on_validate_pressed(self, event: Button.Pressed) -> None:
        self._run_validation()

    @work
    async def _run_validation(self) -> None:
        status = self.query_one("#linear-status", Static)
        next_btn = self.query_one("#wizard-next", Button)
        api_key = self.query_one("#linear-api-key", SecretInput).value.strip()
        team_id = self.query_one("#linear-team-id", SecretInput).value.strip()

        status.update("Validating API key...")
        ok, msg = await validate_linear_key(api_key)
        if not ok:
            status.update(f"[red]{msg}[/red]")
            next_btn.disabled = True
            return

        status.update(f"{msg}. Validating team...")
        ok2, msg2 = await validate_linear_team(api_key, team_id)
        if not ok2:
            status.update(f"[red]{msg2}[/red]")
            next_btn.disabled = True
            return

        status.update(f"[green]{msg} | {msg2}[/green]")
        self._controller.data.linear_api_key = api_key
        self._controller.data.linear_team_id = team_id
        next_btn.disabled = False
