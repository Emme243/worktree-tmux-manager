"""DirectoryInput — Label + Input + directory AutoComplete composed widget."""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Label
from textual_autocomplete import AutoComplete, DropdownItem, TargetState


def _get_directory_suggestions(path_text: str) -> list[DropdownItem]:
    """Return immediate-subdirectory suggestions for *path_text*.

    - Returns [] if no '/' is present (nothing to navigate into yet).
    - Expands a leading '~' before scanning.
    - Returns [] if the parent directory does not exist or is unreadable.
    - Only directories are included (no files).
    - Appends '/' to each suggestion name.
    - Sorted case-insensitively.
    """
    if "/" not in path_text:
        return []

    if path_text.startswith("~"):
        try:
            expanded = str(Path(path_text).expanduser())
        except RuntimeError:
            return []
    else:
        expanded = path_text

    # If the original text ended with '/', the user wants the contents of that
    # directory — use the fully-expanded path as the scan target directly.
    # (Path.expanduser() strips any trailing slash, so we must check first.)
    if path_text.endswith("/"):
        dir_path = expanded
    else:
        last_slash = expanded.rindex("/")
        dir_path = expanded[:last_slash] or "/"

    try:
        entries = sorted(
            (e for e in os.scandir(dir_path) if e.is_dir()),
            key=lambda e: e.name.lower(),
        )
    except OSError:
        return []

    return [DropdownItem(main=entry.name + "/") for entry in entries]


class _DirectoryAutoComplete(AutoComplete):
    """AutoComplete subclass that completes directory paths."""

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        return _get_directory_suggestions(
            target_state.text[: target_state.cursor_position]
        )

    def get_search_string(self, target_state: TargetState) -> str:
        """Return only the segment after the last '/' (the part being typed)."""
        current = target_state.text[: target_state.cursor_position]
        if current.startswith("~"):
            try:
                current = str(Path(current).expanduser())
            except RuntimeError:
                pass
        if "/" in current:
            return current[current.rindex("/") + 1 :]
        return current

    def apply_completion(self, value: str, state: TargetState) -> None:
        """Replace only the segment after the last '/' with *value*."""
        text, cursor = state.text, state.cursor_position
        try:
            replace_start = text.rindex("/", 0, cursor)
        except ValueError:
            new_value = value
            new_cursor = len(value)
        else:
            prefix = text[: replace_start + 1]
            new_value = prefix + value
            new_cursor = len(prefix) + len(value)

        with self.prevent(Input.Changed):
            self.target.value = new_value
            self.target.cursor_position = new_cursor

    def post_completion(self) -> None:
        if not self.target.value.endswith("/"):
            self.action_hide()


class DirectoryInput(Widget):
    """Label + Input + directory AutoComplete for selecting a filesystem path."""

    DEFAULT_CSS = "DirectoryInput { height: auto; }"

    def __init__(
        self,
        label: str = "Path:",
        value: str = "",
        placeholder: str = "/path/to/directory",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._label = label
        self._initial_value = value
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        path_input = Input(
            value=self._initial_value,
            placeholder=self._placeholder,
            id="dir-input",
        )
        yield path_input
        yield _DirectoryAutoComplete(path_input, id="dir-autocomplete")

    @property
    def value(self) -> str:
        """Current raw text in the input (~ not expanded)."""
        return self.query_one("#dir-input", Input).value
