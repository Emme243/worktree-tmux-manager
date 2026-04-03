"""Tests for modules.screens.worktree_list — WorktreeListScreen."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from rich.text import Text
from textual.widgets import Button, DataTable, Footer, Input, Static

from modules.git.models import GitError, WorkingTreeStatus, WorktreeInfo
from modules.screens.worktree_list import WorktreeListScreen
from modules.tmux import TmuxError
from modules.widgets import SearchBar, VimDataTable

from .conftest import ScreenTestApp, wait_ready

# ---------------------------------------------------------------------------
# Helper — create screen app with all mocks active
# ---------------------------------------------------------------------------


def _make_app(repo_dir: str = "/home/user/repos/project") -> ScreenTestApp:
    return ScreenTestApp(lambda: WorktreeListScreen(repo_dir=repo_dir))


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestWorktreeListScreenInit:
    def test_stores_repo_dir(self):
        screen = WorktreeListScreen(repo_dir="/repo")
        assert screen.repo_dir == "/repo"

    def test_initial_worktrees_empty(self):
        screen = WorktreeListScreen(repo_dir="/repo")
        assert screen.worktrees == []

    def test_initial_tmux_statuses_empty(self):
        screen = WorktreeListScreen(repo_dir="/repo")
        assert screen._tmux_statuses == {}


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestWorktreeListScreenCompose:
    async def test_renders_repo_title(self, all_screen_mocks):
        app = _make_app("/home/user/repos/project")
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            title = app.screen.query_one("#wt-title", Static)
            assert "/home/user/repos/project" in title.render().plain

    async def test_renders_table(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table is not None

    async def test_renders_search_bar(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            bar = app.screen.query_one("#search-bar", SearchBar)
            assert bar is not None

    async def test_renders_action_buttons(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            create = app.screen.query_one("#create-btn", Button)
            delete = app.screen.query_one("#delete-btn", Button)
            rename = app.screen.query_one("#rename-btn", Button)
            assert "C" in create.label.plain
            assert "D" in delete.label.plain
            assert "N" in rename.label.plain

    async def test_renders_footer(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            footer = app.screen.query_one(Footer)
            assert footer is not None

    async def test_table_has_six_columns(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert len(table.columns) == 6


# ---------------------------------------------------------------------------
# Data loading / refresh
# ---------------------------------------------------------------------------


class TestWorktreeListScreenRefresh:
    async def test_on_mount_calls_list_worktrees(self, all_screen_mocks):
        app = _make_app("/home/user/repos/project")
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            all_screen_mocks["list_worktrees"].assert_called_with(
                "/home/user/repos/project"
            )

    async def test_on_mount_calls_populate_statuses(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            all_screen_mocks["populate_statuses"].assert_called_once()

    async def test_table_populated_with_worktrees(
        self, all_screen_mocks, sample_worktrees
    ):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == len(sample_worktrees)

    async def test_tmux_statuses_cached_for_non_bare(
        self, all_screen_mocks, sample_worktrees
    ):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            screen = app.screen
            # Bare worktrees should NOT be in tmux cache
            assert "project" not in screen._tmux_statuses
            # Non-bare worktrees should be cached
            assert "feature-login" in screen._tmux_statuses
            assert "bugfix-nav" in screen._tmux_statuses

    async def test_git_error_during_refresh_shows_notification(
        self, mock_populate_statuses, mock_tmux_active
    ):
        with patch(
            "modules.screens.worktree_list.list_worktrees",
            new_callable=AsyncMock,
            side_effect=GitError("repo not found"),
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                table = app.screen.query_one("#wt-table", VimDataTable)
                assert table.row_count == 0

    async def test_action_refresh_triggers_reload(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            all_screen_mocks["list_worktrees"].reset_mock()
            app.screen.action_refresh()
            await pilot.pause()
            await app.workers.wait_for_complete()
            all_screen_mocks["list_worktrees"].assert_called_once()


# ---------------------------------------------------------------------------
# Tmux indicator
# ---------------------------------------------------------------------------


class TestWorktreeListScreenTmuxIndicator:
    async def test_bare_worktree_shows_dash(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            screen = app.screen
            bare_wt = screen.worktrees[0]
            indicator = screen._tmux_indicator(bare_wt)
            assert isinstance(indicator, Text)
            assert indicator.plain == "-"

    async def test_inactive_session_shows_inactive(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            screen = app.screen
            wt = screen.worktrees[1]
            indicator = screen._tmux_indicator(wt)
            assert indicator.plain == "inactive"

    async def test_active_session_shows_active(
        self, mock_list_worktrees, mock_populate_statuses
    ):
        with patch(
            "modules.screens.worktree_list.is_worktree_session_active",
            return_value=True,
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                screen = app.screen
                wt = screen.worktrees[1]
                indicator = screen._tmux_indicator(wt)
                assert indicator.plain == "active"


# ---------------------------------------------------------------------------
# _get_selected_worktree
# ---------------------------------------------------------------------------


class TestWorktreeListScreenGetSelected:
    async def test_returns_worktree_at_cursor(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)
            wt = app.screen._get_selected_worktree()
            assert wt is not None
            assert wt.branch == "feature/login"

    async def test_returns_none_when_table_empty(
        self, mock_populate_statuses, mock_tmux_active
    ):
        with patch(
            "modules.screens.worktree_list.list_worktrees",
            new_callable=AsyncMock,
            return_value=[],
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                wt = app.screen._get_selected_worktree()
                assert wt is None

    async def test_returns_none_when_cursor_out_of_bounds(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            # Force worktrees list to be shorter than the table cursor
            app.screen.worktrees = []
            wt = app.screen._get_selected_worktree()
            assert wt is None

    async def test_returns_none_on_unexpected_exception(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            # Make cursor_row property raise to trigger the except branch
            with patch.object(
                type(table),
                "cursor_row",
                new_callable=lambda: property(
                    lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
                ),
            ):
                wt = app.screen._get_selected_worktree()
                assert wt is None


# ---------------------------------------------------------------------------
# Actions — create / delete / rename
# ---------------------------------------------------------------------------


class TestWorktreeListScreenActions:
    async def test_action_create_pushes_add_modal(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            with patch.object(app, "push_screen") as mock_push:
                app.screen.action_create()
                mock_push.assert_called_once()
                args = mock_push.call_args
                from modules.modals import AddWorktreeModal

                assert isinstance(args[0][0], AddWorktreeModal)

    async def test_action_delete_pushes_remove_modal(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)  # non-bare worktree
            with patch.object(app, "push_screen") as mock_push:
                app.screen.action_delete()
                mock_push.assert_called_once()
                args = mock_push.call_args
                from modules.modals import RemoveWorktreeModal

                assert isinstance(args[0][0], RemoveWorktreeModal)

    async def test_action_delete_does_nothing_when_no_selection(
        self, mock_populate_statuses, mock_tmux_active
    ):
        with patch(
            "modules.screens.worktree_list.list_worktrees",
            new_callable=AsyncMock,
            return_value=[],
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                with patch.object(app, "push_screen") as mock_push:
                    app.screen.action_delete()
                    mock_push.assert_not_called()

    async def test_action_rename_pushes_rename_modal(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)  # non-bare worktree
            with patch.object(app, "push_screen") as mock_push:
                app.screen.action_rename()
                mock_push.assert_called_once()
                args = mock_push.call_args
                from modules.modals import RenameWorktreeModal

                assert isinstance(args[0][0], RenameWorktreeModal)

    async def test_action_rename_blocks_bare_worktree(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=0)  # bare worktree
            with patch.object(app, "push_screen") as mock_push:
                app.screen.action_rename()
                mock_push.assert_not_called()

    async def test_action_rename_does_nothing_when_no_selection(
        self, mock_populate_statuses, mock_tmux_active
    ):
        with patch(
            "modules.screens.worktree_list.list_worktrees",
            new_callable=AsyncMock,
            return_value=[],
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                with patch.object(app, "push_screen") as mock_push:
                    app.screen.action_rename()
                    mock_push.assert_not_called()


# ---------------------------------------------------------------------------
# Modal dismiss callback
# ---------------------------------------------------------------------------


class TestWorktreeListScreenModalCallback:
    async def test_modal_dismiss_true_triggers_refresh(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            all_screen_mocks["list_worktrees"].reset_mock()
            app.screen._on_modal_dismiss(True)
            await pilot.pause()
            await app.workers.wait_for_complete()
            all_screen_mocks["list_worktrees"].assert_called_once()

    async def test_modal_dismiss_false_does_not_refresh(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            all_screen_mocks["list_worktrees"].reset_mock()
            app.screen._on_modal_dismiss(False)
            await pilot.pause()
            await app.workers.wait_for_complete()
            all_screen_mocks["list_worktrees"].assert_not_called()

    async def test_modal_dismiss_none_does_not_refresh(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            all_screen_mocks["list_worktrees"].reset_mock()
            app.screen._on_modal_dismiss(None)
            await pilot.pause()
            await app.workers.wait_for_complete()
            all_screen_mocks["list_worktrees"].assert_not_called()


# ---------------------------------------------------------------------------
# Button routing
# ---------------------------------------------------------------------------


class TestWorktreeListScreenButtons:
    async def test_create_button_calls_action_create(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            with patch.object(app, "push_screen") as mock_push:
                await pilot.click("#create-btn")
                await pilot.pause()
                mock_push.assert_called_once()

    async def test_delete_button_calls_action_delete(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)
            with patch.object(app, "push_screen") as mock_push:
                await pilot.click("#delete-btn")
                await pilot.pause()
                mock_push.assert_called_once()

    async def test_rename_button_calls_action_rename(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)
            with patch.object(app, "push_screen") as mock_push:
                await pilot.click("#rename-btn")
                await pilot.pause()
                mock_push.assert_called_once()


# ---------------------------------------------------------------------------
# Enter worktree (tmux)
# ---------------------------------------------------------------------------


class TestWorktreeListScreenEnterWorktree:
    async def test_enter_bare_worktree_blocked(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=0)  # bare
            with patch(
                "modules.screens.worktree_list.build_session_config"
            ) as mock_cfg:
                app.screen.action_enter_worktree()
                mock_cfg.assert_not_called()

    async def test_enter_worktree_builds_config_and_enters(
        self,
        all_screen_mocks,
        mock_build_session_config,
        mock_enter_worktree_session,
    ):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)  # non-bare
            with patch.object(app, "suspend"):
                app.screen.action_enter_worktree()
            mock_build_session_config.assert_called_once()
            mock_enter_worktree_session.assert_called_once()

    async def test_enter_worktree_does_nothing_when_empty(
        self, mock_populate_statuses, mock_tmux_active
    ):
        with patch(
            "modules.screens.worktree_list.list_worktrees",
            new_callable=AsyncMock,
            return_value=[],
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                with patch(
                    "modules.screens.worktree_list.build_session_config"
                ) as mock_cfg:
                    app.screen.action_enter_worktree()
                    mock_cfg.assert_not_called()

    async def test_tmux_error_shows_notification(
        self,
        all_screen_mocks,
        mock_build_session_config,
    ):
        with patch(
            "modules.screens.worktree_list.enter_worktree_session",
            side_effect=TmuxError("session failed"),
        ):
            app = _make_app()
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                table = app.screen.query_one("#wt-table", VimDataTable)
                table.move_cursor(row=1)
                # Should not raise — error is caught and shown as notification
                with patch.object(app, "suspend"):
                    app.screen.action_enter_worktree()


# ---------------------------------------------------------------------------
# Search / filter
# ---------------------------------------------------------------------------


class TestWorktreeListScreenSearch:
    async def test_slash_key_shows_search_bar(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.focus()
            await pilot.press("slash")
            await pilot.pause()
            bar = app.screen.query_one("#search-bar", SearchBar)
            assert bar.display is True

    async def test_slash_key_ignored_when_input_focused(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            # Focus the search input so that screen.focused is an Input
            bar = app.screen.query_one("#search-bar", SearchBar)
            bar.show_bar()
            await pilot.pause()
            search_input = bar.query_one("#search-input", Input)
            search_input.focus()
            await pilot.pause()
            # Pressing slash while input is focused should type "/" not trigger search action
            with patch.object(app.screen, "action_search") as mock_search:
                await pilot.press("slash")
                await pilot.pause()
                mock_search.assert_not_called()

    async def test_filter_by_name_reduces_rows(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("feature")
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == 1

    async def test_filter_by_branch_reduces_rows(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("bugfix")
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == 1

    async def test_filter_case_insensitive(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("FEATURE")
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == 1

    async def test_filter_no_match_keeps_table_empty(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("nonexistent")
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == 0

    async def test_empty_query_shows_all(self, all_screen_mocks, sample_worktrees):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("feature")
            app.screen._filter_worktrees("")
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == len(sample_worktrees)

    async def test_clear_filter_restores_all_rows(
        self, all_screen_mocks, sample_worktrees
    ):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("feature")
            app.screen._clear_filter()
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == len(sample_worktrees)

    async def test_filter_by_status(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("bare")
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == 1

    async def test_search_bar_submitted_triggers_filter(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            event = SearchBar.Submitted(query="feature")
            app.screen.on_search_bar_submitted(event)
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == 1

    async def test_search_bar_dismissed_clears_filter(
        self, all_screen_mocks, sample_worktrees
    ):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            app.screen._filter_worktrees("feature")
            event = SearchBar.Dismissed()
            app.screen.on_search_bar_dismissed(event)
            table = app.screen.query_one("#wt-table", VimDataTable)
            assert table.row_count == len(sample_worktrees)


# ---------------------------------------------------------------------------
# Keybinding actions
# ---------------------------------------------------------------------------


class TestWorktreeListScreenKeybindings:
    async def test_c_key_triggers_create(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.focus()
            with patch.object(app, "push_screen") as mock_push:
                await pilot.press("c")
                await pilot.pause()
                mock_push.assert_called_once()

    async def test_d_key_triggers_delete(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)
            table.focus()
            with patch.object(app, "push_screen") as mock_push:
                await pilot.press("d")
                await pilot.pause()
                mock_push.assert_called_once()

    async def test_n_key_triggers_rename(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)
            table.focus()
            with patch.object(app, "push_screen") as mock_push:
                await pilot.press("n")
                await pilot.pause()
                mock_push.assert_called_once()

    async def test_r_key_triggers_refresh(self, all_screen_mocks):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.focus()
            all_screen_mocks["list_worktrees"].reset_mock()
            await pilot.press("r")
            await pilot.pause()
            await app.workers.wait_for_complete()
            all_screen_mocks["list_worktrees"].assert_called_once()


# ---------------------------------------------------------------------------
# Row selection → enter worktree
# ---------------------------------------------------------------------------


class TestWorktreeListScreenRowSelection:
    async def test_row_selected_event_triggers_enter(
        self,
        all_screen_mocks,
        mock_build_session_config,
        mock_enter_worktree_session,
    ):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            table = app.screen.query_one("#wt-table", VimDataTable)
            table.move_cursor(row=1)
            event = DataTable.RowSelected(
                data_table=table,
                cursor_row=1,
                row_key=table.get_row_at(1),
            )
            with patch.object(app, "suspend"):
                app.screen.on_data_table_row_selected(event)
            mock_build_session_config.assert_called_once()


# ---------------------------------------------------------------------------
# Styled name (main worktree highlight)
# ---------------------------------------------------------------------------


class TestWorktreeListScreenStyledName:
    async def test_main_worktree_name_is_bold_yellow(self, all_screen_mocks):
        app = _make_app("/home/user/repos/project")
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            screen = app.screen
            main_wt = screen.worktrees[0]  # path matches repo_dir
            styled = screen._styled_name(main_wt)
            assert isinstance(styled, Text)
            assert styled.plain == "project"
            assert "bold" in str(styled.style)

    async def test_non_main_worktree_name_is_plain_string(self, all_screen_mocks):
        app = _make_app("/home/user/repos/project")
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            screen = app.screen
            other_wt = screen.worktrees[1]  # path does NOT match repo_dir
            styled = screen._styled_name(other_wt)
            assert isinstance(styled, str)
            assert styled == "feature-login"

    async def test_is_main_worktree_matches_repo_dir(self, all_screen_mocks):
        app = _make_app("/home/user/repos/project")
        async with app.run_test(size=(120, 40)) as pilot:
            await wait_ready(pilot, app)
            screen = app.screen
            assert screen._is_main_worktree(screen.worktrees[0]) is True
            assert screen._is_main_worktree(screen.worktrees[1]) is False
            assert screen._is_main_worktree(screen.worktrees[2]) is False

    async def test_main_worktree_non_bare(
        self, mock_populate_statuses, mock_tmux_active
    ):
        """The main worktree need not be bare — path match is what counts."""
        non_bare_main = [
            WorktreeInfo(
                path="/home/user/repos/project",
                head="aabbccdd",
                branch="main",
                wt_status=WorkingTreeStatus(),
            ),
            WorktreeInfo(
                path="/home/user/repos/feature-login",
                head="11223344",
                branch="feature/login",
                wt_status=WorkingTreeStatus(),
            ),
        ]
        with patch(
            "modules.screens.worktree_list.list_worktrees",
            new_callable=AsyncMock,
            return_value=non_bare_main,
        ):
            app = _make_app("/home/user/repos/project")
            async with app.run_test(size=(120, 40)) as pilot:
                await wait_ready(pilot, app)
                screen = app.screen
                styled = screen._styled_name(screen.worktrees[0])
                assert isinstance(styled, Text)
                assert styled.plain == "project"
