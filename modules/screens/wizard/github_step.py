"""GithubStepScreen — GitHub personal access token setup step."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.widgets import Button, Label, Static

from modules.core.validation import validate_github_token
from modules.widgets.secret_input import SecretInput

from .base_step import WizardStepScreen

__all__ = ["GithubStepScreen"]


class GithubStepScreen(WizardStepScreen):
    """Collect a GitHub personal access token with inline validation.

    Next is disabled until validation passes. The step is skippable —
    skipping leaves ``controller.data.github_token`` as ``None``.
    """

    skippable = True

    def compose_step_content(self) -> ComposeResult:
        yield Label("Configure GitHub Integration")
        yield SecretInput(
            label="GitHub Token:",
            placeholder="ghp_...",
            hint="Needs scopes: repo, read:user",
            id="github-token",
        )
        yield Button("Validate", id="github-validate", variant="default")
        yield Static("", id="github-status")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#wizard-next", Button).disabled = True

    @on(Button.Pressed, "#github-validate")
    def _on_validate_pressed(self, event: Button.Pressed) -> None:
        self._run_validation()

    @work
    async def _run_validation(self) -> None:
        status = self.query_one("#github-status", Static)
        next_btn = self.query_one("#wizard-next", Button)
        token = self.query_one("#github-token", SecretInput).value.strip()

        status.update("Validating token...")
        ok, msg = await validate_github_token(token)
        if not ok:
            status.update(f"[red]{msg}[/red]")
            next_btn.disabled = True
            return

        status.update(f"[green]{msg}[/green]")
        self._controller.data.github_token = token
        next_btn.disabled = False
