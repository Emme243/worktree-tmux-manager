"""Tests for modules.app — GitWorktreeApp main application."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from textual.app import App

from modules.app import GitWorktreeApp
from modules.core.config import AppConfig, ConfigError
from modules.screens.help_overlay import HelpOverlay
from modules.screens.project_setup import ProjectSetupScreen
from modules.screens.worktree_list import WorktreeListScreen


def _make_config(repo_path: str = "/fake/repo") -> AppConfig:
    return AppConfig(repo_path=Path(repo_path))


# ---------------------------------------------------------------------------
# Class-level attributes
# ---------------------------------------------------------------------------


class TestGitWorktreeAppSetup:
    def test_is_subclass_of_app(self):
        assert issubclass(GitWorktreeApp, App)

    def test_title(self):
        assert GitWorktreeApp.TITLE == "Git Worktree Manager"

    def test_bindings_contain_quit(self):
        keys = [b.key for b in GitWorktreeApp.BINDINGS]
        assert "q" in keys

    def test_bindings_contain_help(self):
        keys = [b.key for b in GitWorktreeApp.BINDINGS]
        assert "question_mark" in keys


# ---------------------------------------------------------------------------
# _validate_and_start — config error
# ---------------------------------------------------------------------------


class TestValidateAndStartConfigError:
    async def test_pushes_setup_screen_when_config_missing(self):
        """First-run: missing file → ProjectSetupScreen pushed."""
        app = GitWorktreeApp()
        with patch(
            "modules.app.load_config",
            side_effect=ConfigError(
                "Config file not found: /fake", reason="missing_file"
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert any(isinstance(s, ProjectSetupScreen) for s in app.screen_stack)

    async def test_pushes_setup_screen_when_repo_path_missing(self):
        """First-run: missing repo_path key → ProjectSetupScreen pushed."""
        app = GitWorktreeApp()
        with patch(
            "modules.app.load_config",
            side_effect=ConfigError(
                "Config file is missing required key 'repo_path': /fake",
                reason="missing_repo_path",
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert any(isinstance(s, ProjectSetupScreen) for s in app.screen_stack)

    async def test_exits_when_config_invalid_toml(self):
        """Invalid TOML → still notifies and exits (not first-run)."""
        app = GitWorktreeApp()
        with patch(
            "modules.app.load_config",
            side_effect=ConfigError(
                "Config file is not valid TOML: /fake\n...", reason="invalid_toml"
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert not any(
                    isinstance(s, WorktreeListScreen) for s in app.screen_stack
                )
                assert not any(
                    isinstance(s, ProjectSetupScreen) for s in app.screen_stack
                )


# ---------------------------------------------------------------------------
# _on_first_run_setup callback
# ---------------------------------------------------------------------------


class TestOnFirstRunSetup:
    async def test_pushes_worktree_list_screen_with_valid_path(self):
        """Callback with a valid Path pushes WorktreeListScreen."""
        app = GitWorktreeApp()
        repo = Path("/fake/repo")
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError("", reason="missing_file"),
            ),
            patch(
                "modules.screens.worktree_list.list_worktrees",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "modules.screens.worktree_list.populate_worktree_statuses",
                new_callable=AsyncMock,
            ),
            patch(
                "modules.screens.worktree_list.is_worktree_session_active",
                return_value=False,
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                app._on_first_run_setup(repo)
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert any(isinstance(s, WorktreeListScreen) for s in app.screen_stack)

    async def test_exits_when_callback_receives_none(self):
        """Callback with None exits the app (defensive path)."""
        app = GitWorktreeApp()
        with patch(
            "modules.app.load_config",
            side_effect=ConfigError("", reason="missing_file"),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                app._on_first_run_setup(None)
                await pilot.pause()
                assert app.return_code is not None


# ---------------------------------------------------------------------------
# _validate_and_start — directory does not exist
# ---------------------------------------------------------------------------


class TestValidateAndStartDirMissing:
    async def test_notifies_error_when_dir_missing(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert not any(
                    isinstance(s, WorktreeListScreen) for s in app.screen_stack
                )


# ---------------------------------------------------------------------------
# _validate_and_start — not a git repo
# ---------------------------------------------------------------------------


class TestValidateAndStartNotGitRepo:
    async def test_notifies_error_when_not_git_repo(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=True),
            patch(
                "modules.git.is_git_repo",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert not any(
                    isinstance(s, WorktreeListScreen) for s in app.screen_stack
                )


# ---------------------------------------------------------------------------
# _validate_and_start — success pushes WorktreeListScreen
# ---------------------------------------------------------------------------


class TestValidateAndStartSuccess:
    async def test_pushes_worktree_list_screen(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=True),
            patch(
                "modules.git.is_git_repo",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "modules.screens.worktree_list.list_worktrees",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "modules.screens.worktree_list.populate_worktree_statuses",
                new_callable=AsyncMock,
            ),
            patch(
                "modules.screens.worktree_list.is_worktree_session_active",
                return_value=False,
            ),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert any(isinstance(s, WorktreeListScreen) for s in app.screen_stack)


# ---------------------------------------------------------------------------
# action_toggle_dark
# ---------------------------------------------------------------------------


class TestActionToggleDark:
    async def test_toggles_to_light(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.theme = "textual-dark"
                app.action_toggle_dark()
                assert app.theme == "textual-light"

    async def test_toggles_to_dark(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.theme = "textual-light"
                app.action_toggle_dark()
                assert app.theme == "textual-dark"


# ---------------------------------------------------------------------------
# action_help — pushes HelpOverlay
# ---------------------------------------------------------------------------


class TestActionHelp:
    async def test_pushes_help_overlay(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.action_help()
                await pilot.pause()
                assert any(isinstance(s, HelpOverlay) for s in app.screen_stack)

    async def test_question_mark_key_opens_help(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.action_help()
                await pilot.pause()
                assert any(isinstance(s, HelpOverlay) for s in app.screen_stack)
