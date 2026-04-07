"""SummaryStepScreen — final review and config save step."""

from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.widgets import Button, Static

from modules.core.config import AppConfig, ProjectConfig, save_config

from .base_step import WizardStepScreen

__all__ = ["SummaryStepScreen"]


class SummaryStepScreen(WizardStepScreen):
    """Read-only summary of all collected wizard data.

    Hides the base ``#wizard-next`` button and replaces it with
    ``#summary-finish`` to avoid the base-class MRO double-dismiss issue.
    On finish: builds ``AppConfig`` from ``WizardData``, calls
    ``save_config()``, then dismisses with ``"next"``.
    """

    skippable = False

    def compose_step_content(self) -> ComposeResult:
        d = self._controller.data

        linear_status = (
            f"Linear: configured (key …{d.linear_api_key[-4:]} / team {d.linear_team_id})"
            if d.linear_api_key
            else "Linear: skipped"
        )
        github_status = "GitHub: token set" if d.github_token else "GitHub: skipped"
        project_line = (
            f"Project: {d.project_path}" if d.project_path else "Project: (not set)"
        )
        github_repo_line = f"GitHub repo: {d.github_repo}" if d.github_repo else ""

        summary = "\n".join(
            filter(None, [project_line, github_repo_line, linear_status, github_status])
        )
        yield Static(summary, id="summary-text")
        yield Button("Finish", id="summary-finish", variant="success")

    def on_mount(self) -> None:
        super().on_mount()
        # Hide the base-class Next button — we use #summary-finish instead
        # to prevent the base on_button_pressed from also calling dismiss().
        self.query_one("#wizard-next", Button).display = False

    @on(Button.Pressed, "#summary-finish")
    def _on_finish_pressed(self, event: Button.Pressed) -> None:
        self._save_and_finish()

    @work
    async def _save_and_finish(self) -> None:
        d = self._controller.data
        project_path = d.project_path or Path.home()
        project = ProjectConfig(path=project_path, github_repo=d.github_repo)
        config = AppConfig(
            repo_path=project_path,
            linear_api_key=d.linear_api_key,
            linear_team_id=d.linear_team_id,
            github_token=d.github_token,
            github_repo=d.github_repo,
            projects=[project],
        )
        save_config(config)
        self.dismiss("next")
