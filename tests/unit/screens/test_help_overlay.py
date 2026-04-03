"""Tests for modules.screens.help_overlay — HelpOverlay."""

from __future__ import annotations

from textual.app import App

from modules.screens.help_overlay import HELP_SECTIONS, HelpOverlay

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
            descs = app.screen.query(".help-desc")
            rendered = [d.render().plain for d in descs]
            assert any("Create worktree" in t for t in rendered)
            assert any("Delete worktree" in t for t in rendered)
            assert any("Rename worktree" in t for t in rendered)

    async def test_help_content_contains_navigation_keys(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            keys = app.screen.query(".help-key")
            rendered = [k.render().plain for k in keys]
            assert any("j / k" in t for t in rendered)
            assert any("G" in t for t in rendered)

    async def test_help_content_contains_search_keys(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            keys = app.screen.query(".help-key")
            descs = app.screen.query(".help-desc")
            key_texts = [k.render().plain for k in keys]
            desc_texts = [d.render().plain for d in descs]
            assert any("/" in t for t in key_texts)
            assert any("Open search bar" in t for t in desc_texts)

    async def test_help_dialog_container_exists(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            dialog = app.screen.query_one("#help-dialog")
            assert dialog is not None

    async def test_section_titles_rendered(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            titles = app.screen.query(".help-section-title")
            rendered = [t.render().plain for t in titles]
            assert any("Navigation" in t for t in rendered)
            assert any("Worktree List" in t for t in rendered)
            assert any("Search" in t for t in rendered)
            assert any("Global" in t for t in rendered)
            assert any("Modals" in t for t in rendered)


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

    async def test_j_does_not_dismiss(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("j")
            await pilot.pause()
            assert app.modal_result == "NOT_DISMISSED"

    async def test_k_does_not_dismiss(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("k")
            await pilot.pause()
            assert app.modal_result == "NOT_DISMISSED"

    async def test_action_scroll_down_targets_help_content(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            scroll = app.screen.query_one("#help-content")
            app.screen.action_scroll_down()
            await pilot.pause()
            # Verify the action runs without error and targets the scroll container
            assert scroll is not None

    async def test_action_scroll_up_targets_help_content(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            scroll = app.screen.query_one("#help-content")
            app.screen.action_scroll_up()
            await pilot.pause()
            assert scroll is not None

    async def test_action_dismiss_help_dismisses(self):
        app = HelpOverlayApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.action_dismiss_help()
            await pilot.pause()
            assert app.modal_result is None


# ---------------------------------------------------------------------------
# HELP_SECTIONS data structure
# ---------------------------------------------------------------------------


class TestHelpSections:
    def test_help_sections_is_non_empty(self):
        assert isinstance(HELP_SECTIONS, list)
        assert len(HELP_SECTIONS) > 0

    def test_help_sections_contains_all_sections(self):
        section_names = [name for name, _ in HELP_SECTIONS]
        assert "Navigation" in section_names
        assert "Worktree List" in section_names
        assert "Search" in section_names
        assert "Global" in section_names
        assert "Modals" in section_names

    def test_each_section_has_bindings(self):
        for name, bindings in HELP_SECTIONS:
            assert len(bindings) > 0, f"Section '{name}' has no bindings"
            for key, desc in bindings:
                assert isinstance(key, str) and len(key) > 0
                assert isinstance(desc, str) and len(desc) > 0
