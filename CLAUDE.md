# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

tt-tmux is a Textual TUI for managing Git worktrees with tmux integration. It targets a hardcoded repo path (`~/projects/turntable`) and provides interactive worktree CRUD, real-time status, and automatic tmux session launching.

## Commands

```bash
# Install dependencies (uses uv package manager)
uv sync --group dev

# Run the app
uv run python main.py

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run a single test file
uv run pytest tests/unit/git/test_operations.py

# Run a specific test
uv run pytest tests/unit/git/test_operations.py::test_function_name -v
```

No linter or formatter is currently configured.

## Architecture

**Layered design** — UI (Textual) → Business logic (git/tmux operations) → Subprocess calls.

- **Entry point:** `main.py` → instantiates `GitWorktreeApp` from `modules/app.py`
- **`modules/git/`** — Async git operations via `asyncio.create_subprocess_exec`. All commands use `git -C <repo_dir>` to avoid chdir. Porcelain format parsing for machine-readable output. Concurrent status fetching with `asyncio.gather()`.
- **`modules/tmux/`** — Synchronous tmux operations (must run inside `app.suspend()` context since tmux needs terminal control). Session template: 3 windows (editor/claude/serve) with `tt-{name}` naming.
- **`modules/screens/`** — Textual Screen classes. `WorktreeListScreen` is the main dashboard with a `VimDataTable`.
- **`modules/modals/`** — Modal dialogs for create/delete/rename worktree operations.
- **`modules/widgets/`** — Custom Textual widgets: `VimDataTable` (DataTable + vim nav), `SearchBar` (toggleable filter input).
- **`styles.tcss`** — Textual CSS styling.

## Key Conventions

- **Async/sync split:** Git operations are async (non-blocking UI). Tmux operations are sync (require `app.suspend()`).
- **Models + operations pattern:** Each module has `models.py` (dataclasses + custom exceptions) and `operations.py` (logic + subprocess calls).
- **`__init__.py` exports:** Each package uses `__all__` to define its public API.
- **Test structure mirrors source:** `tests/unit/[module]/test_[file].py`. Each test subdirectory has its own `conftest.py` with fixtures.
- **Test markers:** `@pytest.mark.slow`, `@pytest.mark.integration`.
- **pytest-asyncio:** Uses `asyncio_mode = "auto"` — async test functions are auto-detected.

## Dependencies

- **Runtime:** `textual>=0.40`
- **Dev:** `pytest>=8.0`, `pytest-asyncio>=0.24`, `pytest-cov>=5.0`
- **Build backend:** hatchling
- **Python:** 3.11+ (see `.python-version`)
