"""Tests for modules.widgets.secret_input."""

from __future__ import annotations

from textual.widgets import Button, Input, Label, Static

from modules.widgets.secret_input import SecretInput

from .conftest import SecretInputApp

# ---------------------------------------------------------------------------
# SecretInput.compose — widget structure
# ---------------------------------------------------------------------------


class TestSecretInputCompose:
    async def test_contains_label(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            assert widget.query_one(Label) is not None

    async def test_contains_input(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            assert widget.query_one("#secret-input", Input) is not None

    async def test_contains_hint(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            assert widget.query_one("#secret-hint", Static) is not None

    async def test_contains_toggle_button(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            assert widget.query_one("#secret-toggle", Button) is not None

    async def test_custom_label_text(self):
        app = SecretInputApp(label="Linear API Key:")
        async with app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            label = widget.query_one(Label)
            assert "Linear API Key:" in label.render().plain


# ---------------------------------------------------------------------------
# Masking behaviour
# ---------------------------------------------------------------------------


class TestSecretInputMasking:
    async def test_masked_by_default(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            inp = widget.query_one("#secret-input", Input)
            assert inp.password is True

    async def test_toggle_button_label_is_show_when_masked(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            btn = widget.query_one("#secret-toggle", Button)
            assert str(btn.label) == "Show"

    async def test_toggle_reveals(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            btn = widget.query_one("#secret-toggle", Button)
            btn.press()
            await pilot.pause()
            inp = widget.query_one("#secret-input", Input)
            assert inp.password is False
            assert str(btn.label) == "Hide"

    async def test_toggle_hides_again(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            btn = widget.query_one("#secret-toggle", Button)
            btn.press()
            await pilot.pause()
            btn.press()
            await pilot.pause()
            inp = widget.query_one("#secret-input", Input)
            assert inp.password is True
            assert str(btn.label) == "Show"


# ---------------------------------------------------------------------------
# .value property
# ---------------------------------------------------------------------------


class TestSecretInputValue:
    async def test_value_returns_input_text(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            widget.query_one("#secret-input", Input).value = "lin_api_abc123"
            assert widget.value == "lin_api_abc123"

    async def test_value_empty_by_default(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            assert widget.value == ""


# ---------------------------------------------------------------------------
# Hint display
# ---------------------------------------------------------------------------


class TestSecretInputHint:
    async def test_empty_hint_hides_hint_widget(self, secret_input_app):
        async with secret_input_app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            hint = widget.query_one("#secret-hint", Static)
            assert hint.display is False

    async def test_nonempty_hint_shows_hint_widget(self):
        app = SecretInputApp(hint="Starts with lin_api_")
        async with app.run_test() as pilot:
            widget = pilot.app.query_one(SecretInput)
            hint = widget.query_one("#secret-hint", Static)
            assert hint.display is True
