"""Tests for modules.widgets.search_bar — toggleable search/filter bar."""

from __future__ import annotations

from unittest.mock import MagicMock

from textual.containers import Horizontal
from textual.widgets import Input, Label

from modules.widgets.search_bar import SearchBar

from .conftest import SearchBarApp

# ---------------------------------------------------------------------------
# Submitted / Dismissed messages
# ---------------------------------------------------------------------------


class TestSubmittedMessage:
    def test_stores_query(self):
        msg = SearchBar.Submitted("hello")
        assert msg.query == "hello"

    def test_empty_query(self):
        msg = SearchBar.Submitted("")
        assert msg.query == ""


class TestDismissedMessage:
    def test_can_instantiate(self):
        msg = SearchBar.Dismissed()
        assert msg is not None


# ---------------------------------------------------------------------------
# SearchBar.compose — widget structure
# ---------------------------------------------------------------------------


class TestSearchBarCompose:
    async def test_contains_horizontal_container(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            assert bar.query_one(Horizontal) is not None

    async def test_contains_search_icon_label(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            label = bar.query_one("#search-icon", Label)
            assert " / " in label.render().plain

    async def test_contains_search_input(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            inp = bar.query_one("#search-input", Input)
            assert inp.placeholder == "Search worktrees..."


# ---------------------------------------------------------------------------
# SearchBar.show_bar
# ---------------------------------------------------------------------------


class TestSearchBarShowBar:
    async def test_sets_display_true(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.display = False
            bar.show_bar()
            assert bar.display is True

    async def test_clears_input_value(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            inp = bar.query_one("#search-input", Input)
            inp.value = "leftover"
            bar.show_bar()
            assert inp.value == ""

    async def test_focuses_input(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.show_bar()
            await pilot.pause()
            focused = pilot.app.focused
            assert isinstance(focused, Input)
            assert focused.id == "search-input"


# ---------------------------------------------------------------------------
# SearchBar.hide_bar
# ---------------------------------------------------------------------------


class TestSearchBarHideBar:
    async def test_sets_display_false(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.display = True
            bar.hide_bar()
            assert bar.display is False


# ---------------------------------------------------------------------------
# SearchBar.on_input_submitted — posts Submitted message
# ---------------------------------------------------------------------------


class TestSearchBarOnInputSubmitted:
    async def test_submitting_input_posts_submitted_message(self, search_bar_app):
        messages: list[SearchBar.Submitted] = []

        class CapturingApp(SearchBarApp):
            def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
                messages.append(event)

        async with CapturingApp().run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.show_bar()
            await pilot.pause()
            inp = bar.query_one("#search-input", Input)
            inp.value = "feature"
            await inp.action_submit()
            await pilot.pause()
            assert len(messages) == 1
            assert messages[0].query == "feature"

    async def test_submitted_strips_whitespace(self, search_bar_app):
        messages: list[SearchBar.Submitted] = []

        class CapturingApp(SearchBarApp):
            def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
                messages.append(event)

        async with CapturingApp().run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.show_bar()
            await pilot.pause()
            inp = bar.query_one("#search-input", Input)
            inp.value = "  hello  "
            await inp.action_submit()
            await pilot.pause()
            assert messages[0].query == "hello"

    async def test_ignores_submit_from_other_input(self, search_bar_app):
        """on_input_submitted only handles #search-input."""
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            # Create a fake event from a different input
            fake_input = MagicMock()
            fake_input.id = "other-input"
            fake_event = MagicMock()
            fake_event.value = "test"
            fake_event.input = fake_input
            # Should not raise or post
            bar.on_input_submitted(fake_event)


# ---------------------------------------------------------------------------
# SearchBar.action_dismiss — hides bar and posts Dismissed
# ---------------------------------------------------------------------------


class TestSearchBarActionDismiss:
    async def test_hides_bar(self, search_bar_app):
        async with search_bar_app.run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.display = True
            bar.action_dismiss()
            assert bar.display is False

    async def test_posts_dismissed_message(self, search_bar_app):
        messages: list[SearchBar.Dismissed] = []

        class CapturingApp(SearchBarApp):
            def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
                messages.append(event)

        async with CapturingApp().run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.display = True
            bar.action_dismiss()
            await pilot.pause()
            assert len(messages) == 1


# ---------------------------------------------------------------------------
# SearchBar.BINDINGS — escape triggers dismiss
# ---------------------------------------------------------------------------


class TestSearchBarBindings:
    async def test_escape_dismisses(self, search_bar_app):
        messages: list[SearchBar.Dismissed] = []

        class CapturingApp(SearchBarApp):
            def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
                messages.append(event)

        async with CapturingApp().run_test() as pilot:
            bar = pilot.app.query_one(SearchBar)
            bar.show_bar()
            await pilot.pause()
            # Focus is on the search input inside the bar
            await pilot.press("escape")
            await pilot.pause()
            assert bar.display is False
            assert len(messages) == 1

    def test_bindings_contain_escape(self):
        bindings = SearchBar.BINDINGS
        keys = [b.key for b in bindings]
        assert "escape" in keys
