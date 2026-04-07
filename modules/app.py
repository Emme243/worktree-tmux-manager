"""Git Worktree Manager — Textual TUI application."""

from __future__ import annotations

import os

from textual import work
from textual.app import App
from textual.binding import Binding

from modules.core.config import ConfigError, ProjectConfig, load_config
from modules.core.state import AppState, load_state, save_state
from modules.screens.help_overlay import HelpOverlay
from modules.screens.project_picker import ProjectPickerScreen
from modules.screens.wizard import (
    GithubStepScreen,
    LinearStepScreen,
    ProjectStepScreen,
    SummaryStepScreen,
    WelcomeStepScreen,
    WizardController,
    WizardStep,
)
from modules.screens.worktree_list import WorktreeListScreen


class GitWorktreeApp(App):
    """A Textual TUI app to manage git worktrees."""

    TITLE = "Git Worktree Manager"
    CSS_PATH = "../styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
    ]

    def on_mount(self) -> None:
        self._validate_and_start()

    @work
    async def _validate_and_start(self) -> None:
        try:
            config = load_config()
            self._config = config
        except ConfigError as exc:
            if exc.reason in ("missing_file", "missing_repo_path"):
                self._run_wizard()
            else:
                self.notify(str(exc), severity="error", timeout=10)
                self.exit()
            return

        state = load_state()

        if len(config.projects) <= 1:
            repo = str(config.repo_path)

            if not os.path.isdir(repo):
                self.notify(
                    f"Directory does not exist: {repo}",
                    severity="error",
                    timeout=10,
                )
                self.exit()
                return

            from modules.git import is_git_repo

            if not await is_git_repo(repo):
                self.notify(
                    f"Not a git repository: {repo}",
                    severity="error",
                    timeout=10,
                )
                self.exit()
                return

            save_state(AppState(last_project_path=config.repo_path))
            self.push_screen(WorktreeListScreen(repo, self._config))
            return

        # Multiple projects — check if last_project_path shortcuts to a known project
        if state.last_project_path is not None:
            matched = next(
                (p for p in config.projects if p.path == state.last_project_path),
                None,
            )
            if matched is not None:
                save_state(AppState(last_project_path=matched.path))
                self.push_screen(WorktreeListScreen(str(matched.path), self._config))
                return

        self.push_screen(
            ProjectPickerScreen(config),
            callback=self._on_project_picked,
        )

    def _on_project_picked(self, result: ProjectConfig | None) -> None:
        if result is None:
            self.exit()
            return
        save_state(AppState(last_project_path=result.path))
        self.push_screen(WorktreeListScreen(str(result.path), self._config))

    def _run_wizard(self) -> None:
        """Create a fresh WizardController and push the first step screen."""
        self._wizard_controller = WizardController()
        self._push_wizard_step()

    def _push_wizard_step(self) -> None:
        """Map the controller's current step to a screen class and push it."""
        step_screens = {
            WizardStep.WELCOME: WelcomeStepScreen,
            WizardStep.LINEAR: LinearStepScreen,
            WizardStep.GITHUB: GithubStepScreen,
            WizardStep.PROJECT: ProjectStepScreen,
            WizardStep.SUMMARY: SummaryStepScreen,
        }
        screen_cls = step_screens[self._wizard_controller.current_step]
        self.push_screen(
            screen_cls(self._wizard_controller),
            callback=self._on_wizard_step_dismissed,
        )

    def _on_wizard_step_dismissed(self, result: str) -> None:
        """Route wizard step results: advance, retreat, finish, or cancel."""
        if result == "cancel":
            self.exit()
            return
        if result in ("next", "skip"):
            if not self._wizard_controller.next():
                self._finish_wizard()
                return
        elif result == "back":
            self._wizard_controller.back()
        self._push_wizard_step()

    def _finish_wizard(self) -> None:
        """Wizard complete: reload config, save state, push WorktreeListScreen."""
        config = load_config()
        self._config = config
        save_state(AppState(last_project_path=config.repo_path))
        self.push_screen(WorktreeListScreen(str(config.repo_path), config))

    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_help(self) -> None:
        self.push_screen(HelpOverlay())
