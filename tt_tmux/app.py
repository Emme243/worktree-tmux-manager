"""Git Worktree Manager — Textual TUI application."""

from __future__ import annotations

import os
from pathlib import Path

from textual import work
from textual.app import App
from textual.binding import Binding

from tt_tmux.screens.help_overlay import HelpOverlay
from tt_tmux.screens.worktree_list import WorktreeListScreen

REPO_DIR = Path.home() / "projects" / "turntable"


class GitWorktreeApp(App):
    """A Textual TUI app to manage git worktrees."""

    TITLE = "Git Worktree Manager"
    CSS_PATH = "../styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help [?]"),
    ]

    def on_mount(self) -> None:
        self._validate_and_start()

    @work
    async def _validate_and_start(self) -> None:
        repo = str(REPO_DIR)

        if not os.path.isdir(repo):
            self.notify(
                f"Directory does not exist: {repo}",
                severity="error",
                timeout=10,
            )
            self.exit()
            return

        from tt_tmux.git import is_git_repo

        if not await is_git_repo(repo):
            self.notify(
                f"Not a git repository: {repo}",
                severity="error",
                timeout=10,
            )
            self.exit()
            return

        self.push_screen(WorktreeListScreen(repo))

    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_help(self) -> None:
        self.push_screen(HelpOverlay())
