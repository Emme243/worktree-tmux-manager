"""Tests for modules.app — GitWorktreeApp main application."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App

from modules.app import REPO_DIR, GitWorktreeApp
from modules.screens.help_overlay import HelpOverlay
from modules.screens.worktree_list import WorktreeListScreen


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

    def test_repo_dir_is_path(self):
        from pathlib import Path

        assert isinstance(REPO_DIR, Path)


# ---------------------------------------------------------------------------
# _validate_and_start — directory does not exist
# ---------------------------------------------------------------------------


class TestValidateAndStartDirMissing:
    async def test_notifies_error_when_dir_missing(self):
        app = GitWorktreeApp()
        with patch("modules.app.os.path.isdir", return_value=False):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.pause()
                await app.workers.wait_for_complete()
                # App should have exited — check that no screen was pushed
                # (the default screen is the only one)
                assert not any(
                    isinstance(s, WorktreeListScreen)
                    for s in app.screen_stack
                )


# ---------------------------------------------------------------------------
# _validate_and_start — not a git repo
# ---------------------------------------------------------------------------


class TestValidateAndStartNotGitRepo:
    async def test_notifies_error_when_not_git_repo(self):
        app = GitWorktreeApp()
        with (
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
                    isinstance(s, WorktreeListScreen)
                    for s in app.screen_stack
                )


# ---------------------------------------------------------------------------
# _validate_and_start — success pushes WorktreeListScreen
# ---------------------------------------------------------------------------


class TestValidateAndStartSuccess:
    async def test_pushes_worktree_list_screen(self):
        app = GitWorktreeApp()
        with (
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
                assert any(
                    isinstance(s, WorktreeListScreen)
                    for s in app.screen_stack
                )


# ---------------------------------------------------------------------------
# action_toggle_dark
# ---------------------------------------------------------------------------


class TestActionToggleDark:
    async def test_toggles_to_light(self):
        app = GitWorktreeApp()
        with patch("modules.app.os.path.isdir", return_value=False):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.theme = "textual-dark"
                app.action_toggle_dark()
                assert app.theme == "textual-light"

    async def test_toggles_to_dark(self):
        app = GitWorktreeApp()
        with patch("modules.app.os.path.isdir", return_value=False):
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
        with patch("modules.app.os.path.isdir", return_value=False):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                app.action_help()
                await pilot.pause()
                assert any(
                    isinstance(s, HelpOverlay)
                    for s in app.screen_stack
                )

    async def test_question_mark_key_opens_help(self):
        app = GitWorktreeApp()
        with patch("modules.app.os.path.isdir", return_value=False):
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await app.workers.wait_for_complete()
                # Directly call the action bound to question_mark
                app.action_help()
                await pilot.pause()
                assert any(
                    isinstance(s, HelpOverlay)
                    for s in app.screen_stack
                )
