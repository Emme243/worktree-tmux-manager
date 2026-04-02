"""Tests for modules.modals.add_worktree — AddWorktreeModal."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import Button, Input, Label, Static
from textual_autocomplete import AutoComplete, DropdownItem

from modules.git.models import GitError
from modules.modals.add_worktree import AddWorktreeModal


# ---------------------------------------------------------------------------
# Helper — wait for modal to be fully mounted and workers to settle
# ---------------------------------------------------------------------------


async def _wait_ready(pilot, app):
    """Pause to let the modal mount, then wait for initial workers."""
    await pilot.pause()
    await pilot.pause()
    await app.workers.wait_for_complete()


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestAddWorktreeModalCompose:
    async def test_renders_title(self, modal_app, mock_list_branches):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            titles = app.screen.query(".modal-title")
            assert len(titles) == 1
            assert "Add Worktree" in titles.first().render().plain

    async def test_renders_branch_input(self, modal_app, mock_list_branches):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            branch_input = app.screen.query_one("#branch-input", Input)
            assert "branch" in branch_input.placeholder.lower()

    async def test_renders_autocomplete(self, modal_app, mock_list_branches):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            ac = app.screen.query_one("#branch-autocomplete", AutoComplete)
            assert ac is not None

    async def test_renders_buttons(self, modal_app, mock_list_branches):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            confirm = app.screen.query_one("#confirm-btn", Button)
            cancel = app.screen.query_one("#cancel-btn", Button)
            assert "Create" in confirm.label.plain
            assert "Cancel" in cancel.label.plain


# ---------------------------------------------------------------------------
# Branch loading
# ---------------------------------------------------------------------------


class TestAddWorktreeModalBranchLoading:
    async def test_loads_branches_on_mount(self, modal_app, mock_list_branches):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            mock_list_branches.assert_called_once_with("/repo")
            assert "main" in app.screen._branches

    async def test_populates_autocomplete_candidates(
        self, modal_app, mock_list_branches
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            ac = app.screen.query_one("#branch-autocomplete", AutoComplete)
            assert len(ac.candidates) == 3
            values = {c.value for c in ac.candidates}
            assert values == {"main", "dev", "feature/login"}

    async def test_branch_load_failure_sets_empty(self, modal_app):
        with patch(
            "modules.modals.add_worktree.list_branches",
            new_callable=AsyncMock,
            side_effect=GitError("network error"),
        ):
            app = modal_app(AddWorktreeModal(repo_dir="/repo"))
            async with app.run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, app)
                assert app.screen._branches == set()


# ---------------------------------------------------------------------------
# Cancel / dismiss
# ---------------------------------------------------------------------------


class TestAddWorktreeModalCancel:
    async def test_cancel_button_dismisses_false(
        self, modal_app, mock_list_branches
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.click("#cancel-btn")
            await pilot.pause()
            assert app.modal_result is False

    async def test_escape_dismisses_false(self, modal_app, mock_list_branches):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestAddWorktreeModalValidation:
    async def test_empty_branch_does_not_call_add(
        self, modal_app, mock_list_branches, mock_add_worktree
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_add_worktree.assert_not_called()

    async def test_whitespace_only_branch_does_not_call_add(
        self, modal_app, mock_list_branches, mock_add_worktree
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/repo"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            app.screen.query_one("#branch-input", Input).value = "   "
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_add_worktree.assert_not_called()


# ---------------------------------------------------------------------------
# Successful creation
# ---------------------------------------------------------------------------


class TestAddWorktreeModalCreate:
    async def test_create_with_existing_branch(
        self, modal_app, mock_list_branches, mock_add_worktree
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/home/user/repos/project"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            app.screen.query_one("#branch-input", Input).value = "main"
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_add_worktree.assert_called_once_with(
                "/home/user/repos/project",
                "/home/user/repos/main",
                "main",
                None,
            )
            assert app.modal_result is True

    async def test_create_with_new_branch(
        self, modal_app, mock_list_branches, mock_add_worktree
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/home/user/repos/project"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            app.screen.query_one("#branch-input", Input).value = "feature/new"
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            # Not in known branches → treated as new branch off "dev"
            mock_add_worktree.assert_called_once_with(
                "/home/user/repos/project",
                "/home/user/repos/feature-new",
                "dev",
                "feature/new",
            )
            assert app.modal_result is True

    async def test_create_with_existing_branch_containing_slash(
        self, modal_app, mock_list_branches, mock_add_worktree
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/home/user/repos/project"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            app.screen.query_one("#branch-input", Input).value = "feature/login"
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            # Existing branch with slash → worktree dir uses dashes
            mock_add_worktree.assert_called_once_with(
                "/home/user/repos/project",
                "/home/user/repos/feature-login",
                "feature/login",
                None,
            )
            assert app.modal_result is True

    async def test_input_submitted_triggers_create(
        self, modal_app, mock_list_branches, mock_add_worktree
    ):
        app = modal_app(AddWorktreeModal(repo_dir="/home/user/repos/project"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot, app)
            app.screen.query_one("#branch-input", Input).value = "dev"
            app.screen.query_one("#branch-input", Input).focus()
            await pilot.press("enter")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_add_worktree.assert_called_once()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestAddWorktreeModalErrors:
    async def test_git_error_does_not_dismiss(self, modal_app, mock_list_branches):
        with patch(
            "modules.modals.add_worktree.add_worktree",
            new_callable=AsyncMock,
            side_effect=GitError("already exists"),
        ):
            app = modal_app(
                AddWorktreeModal(repo_dir="/home/user/repos/project")
            )
            async with app.run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot, app)
                app.screen.query_one("#branch-input", Input).value = "new-feature"
                await pilot.click("#confirm-btn")
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert app.modal_result is None
