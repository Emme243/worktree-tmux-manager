"""Wizard controller — pure Python, no Textual dependency."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "WizardController",
    "WizardData",
    "WizardStep",
]


@dataclass
class WizardData:
    """Collects all values across wizard steps."""

    linear_api_key: str | None = None
    linear_team_id: str | None = None
    github_token: str | None = None
    project_path: Path | None = None
    github_repo: str | None = None


class WizardStep(enum.Enum):
    """Ordered wizard steps."""

    WELCOME = "welcome"
    LINEAR = "linear"
    GITHUB = "github"
    PROJECT = "project"
    SUMMARY = "summary"


class WizardController:
    """Manages wizard navigation state.

    The controller is a plain Python class with no Textual dependency.
    Each wizard step screen holds a reference to the controller, reads its
    state for display, and ``dismiss()``es with a string result.  The app
    orchestrator then calls ``next()`` / ``back()`` / ``skip()`` and pushes
    the appropriate next step screen.

    Steps can be dynamically disabled (e.g. user opts out of Linear
    integration on the welcome screen).  All navigation methods skip
    disabled steps transparently.
    """

    def __init__(
        self,
        steps: list[WizardStep] | None = None,
        data: WizardData | None = None,
    ) -> None:
        self._steps: list[WizardStep] = steps if steps is not None else list(WizardStep)
        self._disabled: set[WizardStep] = set()
        self._index: int = 0
        self.data: WizardData = data if data is not None else WizardData()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_step(self) -> WizardStep:
        """The currently active wizard step."""
        return self._steps[self._index]

    @property
    def is_first(self) -> bool:
        """True when there is no enabled step before the current one."""
        for i in range(self._index - 1, -1, -1):
            if self._steps[i] not in self._disabled:
                return False
        return True

    @property
    def is_last(self) -> bool:
        """True when there is no enabled step after the current one."""
        for i in range(self._index + 1, len(self._steps)):
            if self._steps[i] not in self._disabled:
                return False
        return True

    @property
    def progress(self) -> str:
        """Human-readable progress string, e.g. "Step 2 of 4".

        Only counts enabled steps; disabled steps are excluded from both
        the position and the total.
        """
        enabled = [s for s in self._steps if s not in self._disabled]
        position = enabled.index(self._steps[self._index]) + 1
        return f"Step {position} of {len(enabled)}"

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def next(self) -> bool:
        """Advance to the next enabled step.

        Returns:
            ``True`` if the index changed, ``False`` if already at the last
            enabled step.
        """
        for i in range(self._index + 1, len(self._steps)):
            if self._steps[i] not in self._disabled:
                self._index = i
                return True
        return False

    def back(self) -> bool:
        """Retreat to the previous enabled step.

        Returns:
            ``True`` if the index changed, ``False`` if already at the first
            enabled step.
        """
        for i in range(self._index - 1, -1, -1):
            if self._steps[i] not in self._disabled:
                self._index = i
                return True
        return False

    def skip(self) -> bool:
        """Skip the current step (identical behaviour to ``next()``)."""
        return self.next()

    # ------------------------------------------------------------------
    # Step enable / disable
    # ------------------------------------------------------------------

    def enable(self, step: WizardStep) -> None:
        """Re-enable a previously disabled step."""
        self._disabled.discard(step)

    def disable(self, step: WizardStep) -> None:
        """Disable a step so it is skipped during navigation.

        If *step* is the currently active step, the controller advances
        to the next enabled step.  If no forward step exists, it retreats
        to the previous enabled step.
        """
        self._disabled.add(step)
        if self._steps[self._index] in self._disabled and not self.next():
            self.back()

    def is_enabled(self, step: WizardStep) -> bool:
        """Return ``True`` if *step* is not disabled."""
        return step not in self._disabled
