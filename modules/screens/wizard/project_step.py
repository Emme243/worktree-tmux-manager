"""ProjectStepScreen — git repo path & GitHub repo slug setup step."""

from __future__ import annotations

import re
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input, Label, Static

from modules.git import is_git_repo
from modules.widgets.directory_input import DirectoryInput

from .base_step import WizardStepScreen

__all__ = ["ProjectStepScreen"]

_GITHUB_REPO_RE = re.compile(r"^[^/]+/[^/]+$")


class ProjectStepScreen(WizardStepScreen):
    """Collect the git repository path and optional GitHub repo slug.

    Not skippable — a project path is required to proceed.
    The GitHub repo input is only shown when a GitHub token was configured
    in a prior step (``controller.data.github_token`` is not ``None``).
    """

    skippable = False

    def compose_step_content(self) -> ComposeResult:
        yield Label("Configure Project")
        yield DirectoryInput(
            label="Git repository path:",
            placeholder="~/projects/my-repo",
            id="project-dir-input",
        )
        with Vertical(id="project-github-repo-container"):
            yield Label("GitHub repo (owner/repo):")
            yield Input(placeholder="owner/repo", id="project-github-repo")
        yield Button("Validate", id="project-validate", variant="default")
        yield Static("", id="project-status")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#wizard-next", Button).disabled = True
        if self._controller.data.github_token is None:
            self.query_one("#project-github-repo-container", Vertical).display = False

    @on(Button.Pressed, "#project-validate")
    def _on_validate_pressed(self, event: Button.Pressed) -> None:
        self._run_validation()

    @work
    async def _run_validation(self) -> None:
        status = self.query_one("#project-status", Static)
        next_btn = self.query_one("#wizard-next", Button)
        container = self.query_one("#project-github-repo-container", Vertical)

        raw_path = self.query_one("#project-dir-input", DirectoryInput).value.strip()

        if not raw_path:
            status.update("[red]Please enter a path.[/red]")
            next_btn.disabled = True
            return

        try:
            resolved = Path(raw_path).expanduser().resolve()
        except Exception:
            status.update("[red]Invalid path.[/red]")
            next_btn.disabled = True
            return

        if not resolved.is_dir():
            status.update("[red]Path does not exist or is not a directory.[/red]")
            next_btn.disabled = True
            return

        status.update("Checking git repository...")
        if not await is_git_repo(str(resolved)):
            status.update("[red]Not a git repository.[/red]")
            next_btn.disabled = True
            return

        github_repo: str | None = None
        if container.display:
            github_repo_raw = self.query_one(
                "#project-github-repo", Input
            ).value.strip()
            if not _GITHUB_REPO_RE.match(github_repo_raw):
                status.update("[red]GitHub repo must be in owner/repo format.[/red]")
                next_btn.disabled = True
                return
            github_repo = github_repo_raw

        self._controller.data.project_path = resolved
        self._controller.data.github_repo = github_repo
        status.update("[green]Valid git repository.[/green]")
        next_btn.disabled = False
