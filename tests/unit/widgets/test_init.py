"""Tests for modules.widgets.__init__ — public API exports."""

from __future__ import annotations

from modules.widgets import SearchBar, VimDataTable


class TestWidgetExports:
    def test_exports_search_bar(self):
        assert SearchBar is not None

    def test_exports_vim_data_table(self):
        assert VimDataTable is not None

    def test_all_contains_expected_names(self):
        import modules.widgets as mod

        assert set(mod.__all__) == {"SearchBar", "VimDataTable"}
