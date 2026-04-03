"""Tests for modules.modals.remove_worktree — RemoveWorktreeModal."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from textual.widgets import Button, Checkbox, Label, Static

from modules.git.models import GitError, WorktreeInfo
from modules.modals.remove_worktree import RemoveWorktreeModal, RemoveWorktreeResult

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _wait_ready(pilot):
    """Pause to let the modal mount fully."""
    await pilot.pause()
    await pilot.pause()


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalCompose:
    async def test_renders_title(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            titles = app.screen.query(".modal-title")
            assert len(titles) >= 1
            assert "Delete Worktree" in titles.first().render().plain

    async def test_renders_confirmation_with_worktree_name(
        self, modal_app, clean_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            labels = app.screen.query(Label)
            label_texts = [lbl.render().plain for lbl in labels]
            assert any("my-feature" in t for t in label_texts)

    async def test_renders_buttons(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            confirm = app.screen.query_one("#confirm-btn", Button)
            cancel = app.screen.query_one("#cancel-btn", Button)
            assert "Y" in confirm.label.plain
            assert "N" in cancel.label.plain

    async def test_no_static_warning_for_clean_worktree(
        self, modal_app, clean_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            # No static "uncommitted changes" warning for clean worktrees
            static_warnings = [
                w
                for w in app.screen.query(".modal-warning")
                if w.id != "dynamic-warning"
            ]
            assert len(static_warnings) == 0

    async def test_warning_shown_for_dirty_worktree(self, modal_app, dirty_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", dirty_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warnings = [
                w
                for w in app.screen.query(".modal-warning")
                if w.id != "dynamic-warning"
            ]
            assert len(warnings) == 1

    async def test_no_warning_when_status_is_none(self, modal_app):
        wt = WorktreeInfo(
            path="/home/user/repos/my-feature",
            head="abc12345",
            branch="feature/login",
            wt_status=None,
        )
        app = modal_app(RemoveWorktreeModal("/repo", wt))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warnings = [
                w
                for w in app.screen.query(".modal-warning")
                if w.id != "dynamic-warning"
            ]
            assert len(warnings) == 0

    async def test_delete_branch_checkbox_shown_with_branch_name(
        self, modal_app, clean_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            cb = app.screen.query_one("#delete-branch-cb", Checkbox)
            assert cb.value is True
            assert "feature/login" in cb.label.plain

    async def test_delete_branch_checkbox_hidden_for_detached(
        self, modal_app, detached_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", detached_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            results = app.screen.query("#delete-branch-cb")
            assert len(results) == 0

    async def test_force_checkbox_shown_unchecked(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            cb = app.screen.query_one("#force-cb", Checkbox)
            assert cb.value is False


# ---------------------------------------------------------------------------
# Dynamic warnings
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalDynamicWarnings:
    async def test_dirty_worktree_force_off_warning(self, modal_app, dirty_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", dirty_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warning = app.screen.query_one("#dynamic-warning", Static)
            text = warning.render().plain
            assert "uncommitted changes" in text.lower()
            assert "force" in text.lower()

    async def test_dirty_worktree_force_on_warning(self, modal_app, dirty_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", dirty_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            force_cb = app.screen.query_one("#force-cb", Checkbox)
            force_cb.value = True
            await pilot.pause()
            warning = app.screen.query_one("#dynamic-warning", Static)
            text = warning.render().plain
            assert "permanently lost" in text.lower()

    async def test_locked_worktree_force_off_warning(self, modal_app, locked_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", locked_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warning = app.screen.query_one("#dynamic-warning", Static)
            text = warning.render().plain
            assert "locked" in text.lower()

    async def test_branch_force_off_shows_merge_warning(
        self, modal_app, clean_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warning = app.screen.query_one("#dynamic-warning", Static)
            text = warning.render().plain
            assert "fully merged" in text.lower()

    async def test_branch_force_on_shows_unmerged_warning(
        self, modal_app, clean_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            force_cb = app.screen.query_one("#force-cb", Checkbox)
            force_cb.value = True
            await pilot.pause()
            warning = app.screen.query_one("#dynamic-warning", Static)
            text = warning.render().plain
            assert "unmerged" in text.lower()

    async def test_no_branch_warning_when_unchecked(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            branch_cb = app.screen.query_one("#delete-branch-cb", Checkbox)
            branch_cb.value = False
            await pilot.pause()
            warning = app.screen.query_one("#dynamic-warning", Static)
            assert warning.display is False


# ---------------------------------------------------------------------------
# Cancel / dismiss
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalCancel:
    async def test_cancel_button_dismisses_false(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#cancel-btn")
            await pilot.pause()
            assert app.modal_result is False

    async def test_escape_dismisses_false(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is False

    async def test_q_dismisses_false(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("q")
            await pilot.pause()
            assert app.modal_result is False

    async def test_n_dismisses_false(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("n")
            await pilot.pause()
            assert app.modal_result is False


# ---------------------------------------------------------------------------
# Confirm removal
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalConfirm:
    async def test_confirm_default_removes_without_force(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once_with(
                "/repo", "/home/user/repos/my-feature", force=False
            )

    async def test_confirm_with_force_removes_with_force(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            force_cb = app.screen.query_one("#force-cb", Checkbox)
            force_cb.value = True
            await pilot.pause()
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once_with(
                "/repo", "/home/user/repos/my-feature", force=True
            )

    async def test_confirm_deletes_branch_by_default(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_delete_branch.assert_called_once_with(
                "/repo", "feature/login", force=False
            )

    async def test_confirm_force_deletes_branch_with_force(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            force_cb = app.screen.query_one("#force-cb", Checkbox)
            force_cb.value = True
            await pilot.pause()
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_delete_branch.assert_called_once_with(
                "/repo", "feature/login", force=True
            )

    async def test_confirm_no_branch_delete_when_unchecked(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            branch_cb = app.screen.query_one("#delete-branch-cb", Checkbox)
            branch_cb.value = False
            await pilot.pause()
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once()
            mock_delete_branch.assert_not_called()

    async def test_confirm_no_branch_delete_for_detached(
        self,
        modal_app,
        detached_worktree,
        mock_remove_worktree,
        mock_delete_branch,
    ):
        app = modal_app(RemoveWorktreeModal("/repo", detached_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once()
            mock_delete_branch.assert_not_called()

    async def test_y_key_triggers_confirm(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("y")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once()
            assert isinstance(app.modal_result, RemoveWorktreeResult)

    async def test_result_is_dataclass_on_success(
        self, modal_app, clean_worktree, mock_remove_worktree, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            result = app.modal_result
            assert isinstance(result, RemoveWorktreeResult)
            assert result.success is True
            assert result.branch_deleted is True
            assert result.branch_delete_error is None


# ---------------------------------------------------------------------------
# Locked worktree
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalLocked:
    async def test_locked_force_uses_double_force(
        self, modal_app, locked_worktree, mock_run_git, mock_delete_branch
    ):
        app = modal_app(RemoveWorktreeModal("/repo", locked_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            force_cb = app.screen.query_one("#force-cb", Checkbox)
            force_cb.value = True
            await pilot.pause()
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_run_git.assert_called_once_with(
                "/repo",
                "worktree",
                "remove",
                "--force",
                "--force",
                "/home/user/repos/my-locked",
            )


# ---------------------------------------------------------------------------
# Error handling / partial failure
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalErrors:
    async def test_git_error_does_not_dismiss(
        self, modal_app, clean_worktree, mock_delete_branch
    ):
        with patch(
            "modules.modals.remove_worktree.remove_worktree",
            new_callable=AsyncMock,
            side_effect=GitError("worktree is locked"),
        ):
            app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
            async with app.run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot)
                await pilot.click("#confirm-btn")
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert app.modal_result is None
                mock_delete_branch.assert_not_called()

    async def test_branch_delete_fails_still_dismisses(
        self, modal_app, clean_worktree, mock_remove_worktree
    ):
        with patch(
            "modules.modals.remove_worktree.delete_branch",
            new_callable=AsyncMock,
            side_effect=GitError("branch not fully merged"),
        ):
            app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
            async with app.run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot)
                await pilot.click("#confirm-btn")
                await pilot.pause()
                await app.workers.wait_for_complete()
                result = app.modal_result
                assert isinstance(result, RemoveWorktreeResult)
                assert result.success is True
                assert result.branch_deleted is False
                assert result.branch_delete_error is not None
