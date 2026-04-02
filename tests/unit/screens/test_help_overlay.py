"""Tests for tt_tmux.screens.help_overlay — HelpOverlay."""

from __future__ import annotations

import pytest
from textual.app import App
from textual.widgets import Static

from tt_tmux.screens.help_overlay import HELP_TEXT, HelpOverlay


# ---------------------------------------------------------------------------
# Host app for testing the modal overlay
# ---------------------------------------------------------------------------


class HelpOverlayApp(App):
    """Minimal app that pushes HelpOverlay and captures dismiss result."""

    def __init__(self):
        super().__init__()
        self.modal_result: None | str = "NOT_DISMISSED"

    def on_mount(self) -> None:
        self.push_screen(HelpOverlay(), callback=self._on_dismiss)

    def _on_dismiss(self, result) -> None:
        self.modal_result = result


async def _wait_ready(pilot):
    await pilot.pause()
    await pilot.pause()


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestHelpOverlayCompose:
    async def test_renders_title(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            titles = app.screen.query(".modal-title")
            assert len(titles) == 1
            assert "Keyboard Shortcuts" in titles.first().render().plain

    async def test_renders_help_content(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            content = app.screen.query_one("#help-content", Static)
            rendered = content.render().plain
            assert "Create worktree" in rendered
            assert "Delete worktree" in rendered
            assert "Rename worktree" in rendered

    async def test_help_content_contains_navigation_keys(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            content = app.screen.query_one("#help-content", Static)
            rendered = content.render().plain
            assert "j / k" in rendered
            assert "G" in rendered

    async def test_help_content_contains_search_keys(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            content = app.screen.query_one("#help-content", Static)
            rendered = content.render().plain
            assert "/" in rendered
            assert "Open search bar" in rendered

    async def test_help_dialog_container_exists(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            dialog = app.screen.query_one("#help-dialog")
            assert dialog is not None


# ---------------------------------------------------------------------------
# Dismiss behaviour
# ---------------------------------------------------------------------------


class TestHelpOverlayDismiss:
    async def test_escape_dismisses_with_none(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is None

    async def test_question_mark_dismisses_with_none(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("question_mark")
            await pilot.pause()
            assert app.modal_result is None

    async def test_action_dismiss_help_dismisses(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.action_dismiss_help()
            await pilot.pause()
            assert app.modal_result is None


# ---------------------------------------------------------------------------
# HELP_TEXT constant
# ---------------------------------------------------------------------------


class TestHelpText:
    def test_help_text_is_non_empty_string(self):
        assert isinstance(HELP_TEXT, str)
        assert len(HELP_TEXT) > 0

    def test_help_text_contains_all_sections(self):
        assert "Navigation" in HELP_TEXT
        assert "Worktree List" in HELP_TEXT
        assert "Search" in HELP_TEXT
        assert "Global" in HELP_TEXT
        assert "Modals" in HELP_TEXT
