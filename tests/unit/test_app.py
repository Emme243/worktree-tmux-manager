"""Tests for modules.app — GitWorktreeApp main application."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from textual.app import App

from modules.app import GitWorktreeApp
from modules.core.config import AppConfig, ConfigError, ProjectConfig
from modules.core.state import AppState
from modules.screens.help_overlay import HelpOverlay
from modules.screens.project_picker import ProjectPickerScreen
from modules.screens.project_setup import ProjectSetupScreen
from modules.screens.worktree_list import WorktreeListScreen


def _make_config(repo_path: str = "/fake/repo") -> AppConfig:
    return AppConfig(repo_path=Path(repo_path))


def _make_multi_config(paths: list[str]) -> AppConfig:
    projects = [ProjectConfig(path=Path(p)) for p in paths]
    return AppConfig(repo_path=projects[0].path, projects=projects)


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
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError(
                    "Config file not found: /fake", reason="missing_file"
                ),
            ),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError(
                    "Config file is missing required key 'repo_path': /fake",
                    reason="missing_repo_path",
                ),
            ),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError(
                    "Config file is not valid TOML: /fake\n...", reason="invalid_toml"
                ),
            ),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError("", reason="missing_file"),
            ),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
# _validate_and_start — last-used project persistence (M1B-07)
# ---------------------------------------------------------------------------


class TestValidateAndStartLastProject:
    async def test_skips_picker_when_last_project_matches(self):
        """Multi-project: matching last_project_path → WorktreeListScreen, no picker."""
        app = GitWorktreeApp()
        config = _make_multi_config(["/repos/alpha", "/repos/beta"])
        state = AppState(last_project_path=Path("/repos/beta"))
        with (
            patch("modules.app.load_config", return_value=config),
            patch("modules.app.load_state", return_value=state),
            patch("modules.app.save_state"),
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
                assert any(isinstance(s, WorktreeListScreen) for s in app.screen_stack)
                assert not any(
                    isinstance(s, ProjectPickerScreen) for s in app.screen_stack
                )

    async def test_shows_picker_when_last_project_stale(self):
        """Multi-project: last_project_path not in config → ProjectPickerScreen shown."""
        app = GitWorktreeApp()
        config = _make_multi_config(["/repos/alpha", "/repos/beta"])
        state = AppState(last_project_path=Path("/repos/removed"))
        with (
            patch("modules.app.load_config", return_value=config),
            patch("modules.app.load_state", return_value=state),
            patch("modules.app.save_state"),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert any(isinstance(s, ProjectPickerScreen) for s in app.screen_stack)

    async def test_shows_picker_when_state_is_none(self):
        """Multi-project: no last project in state → ProjectPickerScreen shown."""
        app = GitWorktreeApp()
        config = _make_multi_config(["/repos/alpha", "/repos/beta"])
        with (
            patch("modules.app.load_config", return_value=config),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert any(isinstance(s, ProjectPickerScreen) for s in app.screen_stack)

    async def test_saves_state_on_single_project_startup(self):
        """Single project: save_state called with repo_path."""
        app = GitWorktreeApp()
        config = _make_config("/repos/solo")
        with (
            patch("modules.app.load_config", return_value=config),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state") as mock_save,
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
                mock_save.assert_called_once_with(
                    AppState(last_project_path=Path("/repos/solo"))
                )

    async def test_saves_state_on_last_project_shortcut(self):
        """Multi-project shortcut: save_state called with matched project path."""
        app = GitWorktreeApp()
        config = _make_multi_config(["/repos/alpha", "/repos/beta"])
        state = AppState(last_project_path=Path("/repos/beta"))
        with (
            patch("modules.app.load_config", return_value=config),
            patch("modules.app.load_state", return_value=state),
            patch("modules.app.save_state") as mock_save,
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
                mock_save.assert_called_once_with(
                    AppState(last_project_path=Path("/repos/beta"))
                )


# ---------------------------------------------------------------------------
# _on_project_picked — saves state (M1B-07)
# ---------------------------------------------------------------------------


class TestOnProjectPickedSavesState:
    async def test_saves_state_when_project_picked(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state") as mock_save,
            patch("modules.app.os.path.isdir", return_value=False),
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
                await app.workers.wait_for_complete()
                mock_save.reset_mock()
                project = ProjectConfig(path=Path("/repos/alpha"))
                app._on_project_picked(project)
                await pilot.pause()
                mock_save.assert_called_once_with(
                    AppState(last_project_path=Path("/repos/alpha"))
                )

    async def test_does_not_save_state_when_none(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state") as mock_save,
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                mock_save.reset_mock()
                app._on_project_picked(None)
                mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# _on_first_run_setup — saves state (M1B-07)
# ---------------------------------------------------------------------------


class TestOnFirstRunSetupSavesState:
    async def test_saves_state_when_path_returned(self):
        app = GitWorktreeApp()
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError("", reason="missing_file"),
            ),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state") as mock_save,
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
                mock_save.reset_mock()
                app._on_first_run_setup(Path("/new/repo"))
                await pilot.pause()
                mock_save.assert_called_once_with(
                    AppState(last_project_path=Path("/new/repo"))
                )

    async def test_does_not_save_state_when_none(self):
        app = GitWorktreeApp()
        with (
            patch(
                "modules.app.load_config",
                side_effect=ConfigError("", reason="missing_file"),
            ),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state") as mock_save,
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.pause()
                mock_save.reset_mock()
                app._on_first_run_setup(None)
                mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# action_toggle_dark
# ---------------------------------------------------------------------------


class TestActionToggleDark:
    async def test_toggles_to_light(self):
        app = GitWorktreeApp()
        with (
            patch("modules.app.load_config", return_value=_make_config()),
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
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
            patch("modules.app.load_state", return_value=AppState()),
            patch("modules.app.save_state"),
            patch("modules.app.os.path.isdir", return_value=False),
        ):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.action_help()
                await pilot.pause()
                assert any(isinstance(s, HelpOverlay) for s in app.screen_stack)
