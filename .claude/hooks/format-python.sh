#!/usr/bin/env bash
# Claude Code PostToolUse hook: auto-format Python files with ruff after edits.
# Receives JSON on stdin with tool_input.file_path.

set -euo pipefail

# Read the file path from the JSON input on stdin
FILE_PATH=$(cat | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('tool_input', {}).get('file_path', ''))" 2>/dev/null)

# Exit silently if no file path or not a Python file
[[ -z "$FILE_PATH" || "$FILE_PATH" != *.py ]] && exit 0

# Exit silently if file doesn't exist (e.g., was deleted)
[[ ! -f "$FILE_PATH" ]] && exit 0

# Format and fix lint issues
cd "$CLAUDE_PROJECT_DIR"
uv run ruff format "$FILE_PATH" 2>/dev/null || true
uv run ruff check --fix "$FILE_PATH" 2>/dev/null || true
