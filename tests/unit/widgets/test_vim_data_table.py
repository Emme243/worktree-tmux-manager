"""Tests for tt_tmux.widgets.vim_data_table — DataTable with vim navigation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import DataTable

from tt_tmux.widgets.vim_data_table import VimDataTable

from .conftest import VimDataTableApp


# ---------------------------------------------------------------------------
# Inheritance and BINDINGS
# ---------------------------------------------------------------------------


class TestVimDataTableSetup:
    def test_is_subclass_of_data_table(self):
        assert issubclass(VimDataTable, DataTable)

    def test_bindings_contain_j_k_G(self):
        keys = [b.key for b in VimDataTable.BINDINGS]
        assert "j" in keys
        assert "k" in keys
        assert "G" in keys

    def test_g_pending_defaults_false(self):
        table = VimDataTable()
        assert table._g_pending is False


# ---------------------------------------------------------------------------
# j / k navigation — cursor movement
# ---------------------------------------------------------------------------


class TestVimNavigation:
    async def test_j_moves_cursor_down(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            initial = table.cursor_row
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == initial + 1

    async def test_k_moves_cursor_up(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            # Move down first so we can go up
            await pilot.press("j")
            await pilot.press("j")
            await pilot.pause()
            row_before = table.cursor_row
            await pilot.press("k")
            await pilot.pause()
            assert table.cursor_row == row_before - 1

    async def test_G_scrolls_to_bottom(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            await pilot.press("G")
            await pilot.pause()
            # Cursor should be at last row
            assert table.cursor_row == table.row_count - 1


# ---------------------------------------------------------------------------
# gg — scroll to top (double g press)
# ---------------------------------------------------------------------------


class TestVimGGNavigation:
    async def test_gg_scrolls_to_top(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            # Move to bottom first
            await pilot.press("G")
            await pilot.pause()
            assert table.cursor_row == table.row_count - 1
            # Now press gg
            await pilot.press("g")
            await pilot.press("g")
            await pilot.pause()
            assert table.cursor_row == 0

    async def test_first_g_sets_pending(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            assert table._g_pending is False
            await pilot.press("g")
            assert table._g_pending is True

    async def test_second_g_clears_pending(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            await pilot.press("g")
            assert table._g_pending is True
            await pilot.press("g")
            assert table._g_pending is False

    async def test_other_key_clears_g_pending(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            await pilot.press("g")
            assert table._g_pending is True
            await pilot.press("j")
            await pilot.pause()
            assert table._g_pending is False


# ---------------------------------------------------------------------------
# _clear_g_pending — timer callback
# ---------------------------------------------------------------------------


class TestClearGPending:
    def test_clears_pending_flag(self):
        table = VimDataTable()
        table._g_pending = True
        table._clear_g_pending()
        assert table._g_pending is False

    def test_noop_when_already_false(self):
        table = VimDataTable()
        table._g_pending = False
        table._clear_g_pending()
        assert table._g_pending is False

    async def test_timer_clears_pending_after_delay(self, vim_table_app):
        """After pressing g once, the timer should clear _g_pending."""
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            await pilot.press("g")
            assert table._g_pending is True
            # Wait for the 0.5s timer to fire
            import asyncio
            await asyncio.sleep(0.6)
            await pilot.pause()
            assert table._g_pending is False


# ---------------------------------------------------------------------------
# on_key — event prevention
# ---------------------------------------------------------------------------


class TestOnKeyEventHandling:
    async def test_g_prevents_default(self, vim_table_app):
        """Pressing g should prevent default and stop propagation."""
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            # We test via side effect: _g_pending should be set
            await pilot.press("g")
            assert table._g_pending is True

    async def test_gg_calls_action_scroll_top(self, vim_table_app):
        async with vim_table_app.run_test(size=(80, 30)) as pilot:
            table = pilot.app.query_one(VimDataTable)
            table.focus()
            await pilot.pause()
            # Move down first
            await pilot.press("G")
            await pilot.pause()
            assert table.cursor_row > 0
            with patch.object(table, "action_scroll_top", wraps=table.action_scroll_top) as mock_scroll:
                await pilot.press("g")
                await pilot.press("g")
                await pilot.pause()
                mock_scroll.assert_called_once()
