"""Unit tests for WizardController — pure Python, no Textual."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.screens.wizard.controller import WizardController, WizardData, WizardStep

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def ctrl() -> WizardController:
    """A fresh controller with all 5 steps enabled, starting at WELCOME."""
    return WizardController()


# ---------------------------------------------------------------------------
# WizardData
# ---------------------------------------------------------------------------


class TestWizardData:
    def test_defaults_all_none(self) -> None:
        data = WizardData()
        assert data.linear_api_key is None
        assert data.linear_team_id is None
        assert data.github_token is None
        assert data.project_path is None
        assert data.github_repo is None

    def test_can_assign_values(self) -> None:
        data = WizardData()
        data.linear_api_key = "lin_api_123"
        data.project_path = Path("/home/user/repo")
        assert data.linear_api_key == "lin_api_123"
        assert data.project_path == Path("/home/user/repo")


# ---------------------------------------------------------------------------
# WizardStep
# ---------------------------------------------------------------------------


class TestWizardStep:
    def test_enum_members_exist(self) -> None:
        assert WizardStep.WELCOME
        assert WizardStep.LINEAR
        assert WizardStep.GITHUB
        assert WizardStep.PROJECT
        assert WizardStep.SUMMARY

    def test_canonical_order(self) -> None:
        expected = [
            WizardStep.WELCOME,
            WizardStep.LINEAR,
            WizardStep.GITHUB,
            WizardStep.PROJECT,
            WizardStep.SUMMARY,
        ]
        assert list(WizardStep) == expected


# ---------------------------------------------------------------------------
# WizardController — initialisation
# ---------------------------------------------------------------------------


class TestWizardControllerInit:
    def test_starts_at_welcome(self, ctrl: WizardController) -> None:
        assert ctrl.current_step == WizardStep.WELCOME

    def test_default_steps_all_five(self, ctrl: WizardController) -> None:
        assert len(ctrl._steps) == 5

    def test_custom_step_list(self) -> None:
        c = WizardController(steps=[WizardStep.WELCOME, WizardStep.SUMMARY])
        assert c.current_step == WizardStep.WELCOME
        assert len(c._steps) == 2

    def test_data_is_wizard_data_instance(self, ctrl: WizardController) -> None:
        assert isinstance(ctrl.data, WizardData)

    def test_custom_data_injected(self) -> None:
        data = WizardData(linear_api_key="key123")
        c = WizardController(data=data)
        assert c.data.linear_api_key == "key123"


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


class TestWizardControllerNavigation:
    def test_next_advances_step(self, ctrl: WizardController) -> None:
        assert ctrl.next() is True
        assert ctrl.current_step == WizardStep.LINEAR

    def test_next_at_last_returns_false(self, ctrl: WizardController) -> None:
        # Advance to the last step
        for _ in range(4):
            ctrl.next()
        assert ctrl.current_step == WizardStep.SUMMARY
        assert ctrl.next() is False
        assert ctrl.current_step == WizardStep.SUMMARY

    def test_back_retreats_step(self, ctrl: WizardController) -> None:
        ctrl.next()
        assert ctrl.back() is True
        assert ctrl.current_step == WizardStep.WELCOME

    def test_back_at_first_returns_false(self, ctrl: WizardController) -> None:
        assert ctrl.back() is False
        assert ctrl.current_step == WizardStep.WELCOME

    def test_skip_behaves_like_next(self, ctrl: WizardController) -> None:
        assert ctrl.skip() is True
        assert ctrl.current_step == WizardStep.LINEAR

    def test_full_forward_traversal(self, ctrl: WizardController) -> None:
        steps = [ctrl.current_step]
        while ctrl.next():
            steps.append(ctrl.current_step)
        assert steps == list(WizardStep)

    def test_full_round_trip(self, ctrl: WizardController) -> None:
        for _ in range(4):
            ctrl.next()
        for _ in range(4):
            ctrl.back()
        assert ctrl.current_step == WizardStep.WELCOME


# ---------------------------------------------------------------------------
# Boundary properties
# ---------------------------------------------------------------------------


class TestWizardControllerBoundaryProperties:
    def test_is_first_true_at_welcome(self, ctrl: WizardController) -> None:
        assert ctrl.is_first is True

    def test_is_first_false_after_next(self, ctrl: WizardController) -> None:
        ctrl.next()
        assert ctrl.is_first is False

    def test_is_last_true_at_summary(self, ctrl: WizardController) -> None:
        for _ in range(4):
            ctrl.next()
        assert ctrl.is_last is True

    def test_is_last_false_before_summary(self, ctrl: WizardController) -> None:
        ctrl.next()  # on LINEAR
        assert ctrl.is_last is False

    def test_is_first_and_is_last_when_only_one_enabled_step(self) -> None:
        c = WizardController(steps=[WizardStep.SUMMARY])
        assert c.is_first is True
        assert c.is_last is True


# ---------------------------------------------------------------------------
# Progress string
# ---------------------------------------------------------------------------


class TestWizardControllerProgress:
    def test_progress_step_1_of_5(self, ctrl: WizardController) -> None:
        assert ctrl.progress == "Step 1 of 5"

    def test_progress_step_2_of_5(self, ctrl: WizardController) -> None:
        ctrl.next()
        assert ctrl.progress == "Step 2 of 5"

    def test_progress_step_5_of_5(self, ctrl: WizardController) -> None:
        for _ in range(4):
            ctrl.next()
        assert ctrl.progress == "Step 5 of 5"

    def test_progress_excludes_disabled(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        # On WELCOME: "Step 1 of 4"
        assert ctrl.progress == "Step 1 of 4"
        ctrl.next()  # jumps to GITHUB
        assert ctrl.progress == "Step 2 of 4"

    def test_progress_format_string(self, ctrl: WizardController) -> None:
        p = ctrl.progress
        assert p.startswith("Step ")
        assert " of " in p
        parts = p.split()
        assert len(parts) == 4  # ["Step", "1", "of", "5"]


# ---------------------------------------------------------------------------
# Disable / enable
# ---------------------------------------------------------------------------


class TestWizardControllerDisable:
    def test_disable_non_current_step(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        assert ctrl.current_step == WizardStep.WELCOME  # unchanged

    def test_is_enabled_false_after_disable(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        assert ctrl.is_enabled(WizardStep.LINEAR) is False

    def test_enable_restores_step(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        ctrl.enable(WizardStep.LINEAR)
        assert ctrl.is_enabled(WizardStep.LINEAR) is True

    def test_next_skips_disabled_step(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        ctrl.next()
        assert ctrl.current_step == WizardStep.GITHUB

    def test_back_skips_disabled_step(self, ctrl: WizardController) -> None:
        ctrl.next()  # LINEAR
        ctrl.next()  # GITHUB
        ctrl.disable(WizardStep.LINEAR)
        ctrl.back()
        assert ctrl.current_step == WizardStep.WELCOME

    def test_disable_current_step_advances(self, ctrl: WizardController) -> None:
        ctrl.next()  # on LINEAR
        ctrl.disable(WizardStep.LINEAR)
        assert ctrl.current_step == WizardStep.GITHUB

    def test_disable_current_last_step_retreats(self) -> None:
        # On SUMMARY, disable SUMMARY → retreat to previous enabled step
        c = WizardController()
        for _ in range(4):
            c.next()
        assert c.current_step == WizardStep.SUMMARY
        c.disable(WizardStep.SUMMARY)
        assert c.current_step == WizardStep.PROJECT

    def test_disable_middle_two_steps(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        ctrl.disable(WizardStep.GITHUB)
        ctrl.next()
        assert ctrl.current_step == WizardStep.PROJECT

    def test_all_steps_except_current_disabled(self) -> None:
        c = WizardController()
        for step in [
            WizardStep.LINEAR,
            WizardStep.GITHUB,
            WizardStep.PROJECT,
            WizardStep.SUMMARY,
        ]:
            c.disable(step)
        assert c.progress == "Step 1 of 1"
        assert c.is_first is True
        assert c.is_last is True


# ---------------------------------------------------------------------------
# Skip with disabled steps
# ---------------------------------------------------------------------------


class TestWizardControllerSkipDisabled:
    def test_skip_skips_disabled(self, ctrl: WizardController) -> None:
        ctrl.disable(WizardStep.LINEAR)
        ctrl.skip()
        assert ctrl.current_step == WizardStep.GITHUB

    def test_skip_at_last_enabled_returns_false(self, ctrl: WizardController) -> None:
        for _ in range(4):
            ctrl.next()
        assert ctrl.skip() is False


# ---------------------------------------------------------------------------
# Data persistence across navigation
# ---------------------------------------------------------------------------


class TestWizardControllerData:
    def test_data_attribute_is_mutable(self, ctrl: WizardController) -> None:
        ctrl.data.linear_api_key = "lin_api_abc"
        assert ctrl.data.linear_api_key == "lin_api_abc"

    def test_data_persists_across_navigation(self, ctrl: WizardController) -> None:
        ctrl.data.github_token = "ghp_token"
        ctrl.next()
        ctrl.back()
        assert ctrl.data.github_token == "ghp_token"
