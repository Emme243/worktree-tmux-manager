# tt-tmux

A terminal UI for managing Git worktrees with tmux integration, built with [Textual](https://github.com/Textualize/textual).

## Features

- **Worktree management** — Create, delete, and rename git worktrees from an interactive TUI
- **Status overview** — View branch, HEAD commit, git status (clean/dirty), staged/modified/untracked file counts, and active tmux sessions at a glance
- **Tmux integration** — Enter a worktree and automatically get a pre-configured tmux session with editor, Claude CLI, and dev server windows
- **Vim-style navigation** — `j`/`k` movement, `gg`/`G` jumps, `/` search
- **Search & filter** — Filter worktrees by name, branch, or status

## Prerequisites

- **Git** (with worktree support)
- **Tmux**
- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** — Python package manager

## Getting Started

```bash
# Clone the repository
git clone <repo-url> && cd tt-tmux

# Install dependencies (creates .venv automatically)
uv sync --group dev

# Run the app
uv run python main.py
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run a specific test file
uv run pytest tests/unit/git/test_operations.py
```

### Managing Dependencies

```bash
# Add a runtime dependency
uv add <package>

# Add a dev dependency
uv add --group dev <package>

# Sync environment after pulling changes
uv sync --group dev

# Upgrade a specific package
uv lock --upgrade-package <package>
```

## Keybindings

### Navigation

| Key | Action |
|-----|--------|
| `j` / `k` | Move down / up |
| `G` | Jump to bottom |
| `gg` | Jump to top |
| `Tab` / `Shift+Tab` | Next / previous widget |

### Actions

| Key | Action |
|-----|--------|
| `Enter` | Enter worktree tmux session |
| `c` | Create worktree |
| `d` | Delete worktree |
| `r` | Rename worktree |
| `F5` | Refresh list |

### Search

| Key | Action |
|-----|--------|
| `/` | Open search bar |
| `Enter` | Apply filter |
| `Escape` | Clear filter and close |

### Global

| Key | Action |
|-----|--------|
| `?` | Show help |
| `d` | Toggle dark/light theme |
| `q` | Quit |

## Project Structure

```
tt-tmux/
├── main.py                  # Entry point
├── styles.tcss              # Textual CSS styling
├── pyproject.toml           # Project config & dependencies
├── modules/
│   ├── app.py               # Main Textual app
│   ├── git/
│   │   ├── models.py        # GitError, WorktreeInfo, WorkingTreeStatus
│   │   └── operations.py    # Async git command execution
│   ├── tmux/
│   │   ├── models.py        # TmuxError, SessionConfig, WindowConfig
│   │   └── operations.py    # Tmux session management
│   ├── screens/
│   │   ├── worktree_list.py # Main worktree listing screen
│   │   └── help_overlay.py  # Help dialog
│   ├── modals/
│   │   ├── add_worktree.py  # Create worktree modal
│   │   ├── remove_worktree.py
│   │   └── rename_worktree.py
│   └── widgets/
│       ├── vim_data_table.py # DataTable with vim keybindings
│       └── search_bar.py     # Search input widget
└── tests/
    └── unit/                 # Unit tests mirroring modules/ structure
```
