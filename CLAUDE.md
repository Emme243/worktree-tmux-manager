# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Instructions
Always provide a robust and up to date solution for any given task. When working on a task go to the internet and perform a web research on the technologies that are involved in the task so you know how they work and what are capable of doing or not. Prefer and look for the official GitHub repositories of such technologies as your primary source of truth. Visit https://github.com and from there look for the github repositories of the technologies. You are allowed to extend your research to a bigger point if it's needed for solving the given task. Avoid relying on your own knowledge unless it is a straight forward task.

The user might give you some URLs that you can use as starting points of research and task resolution. Remember you should always provide up to date and robust solutions.

Evaluate and analyze the prompt the user gives you to know if it is all clear and there are no side effects. Ask questions to the user for a bigger understanding of the problem, only if you consider it is needed.

Take your time to solve the issue, that is fine. Prefer quality of research and output over speed.

## Project Overview

tt-tmux is a Textual TUI for managing Git worktrees with tmux integration. It is evolving into a multi-project launcher: the user configures one or more git repos via `~/.config/tt-tmux/config.toml`, selects a project from a picker on startup, and lands in a worktree manager for that project. It provides interactive worktree CRUD, real-time status, and automatic tmux session launching.

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

## Linting & Formatting (ruff)

```bash
# Format all files
uv run ruff format modules/ tests/ main.py

# Check lint rules (no auto-fix)
uv run ruff check modules/ tests/ main.py

# Check and auto-fix lint issues
uv run ruff check --fix modules/ tests/ main.py
```

A Claude Code hook auto-runs `ruff format` and `ruff check --fix` on every Python file edit.

## Issue Tracker

Active development work is tracked in [`ISSUES.md`](./ISSUES.md). It is organized into milestones:

- **M1 Foundation** — config system ✅, domain models (Ticket, PullRequest, Comment), branch↔ticket mapping
- **M1-B First-Run & Multi-Project UX** — config write support, directory-autocomplete input, first-run setup screen, multi-project config schema, project picker, last-used project memory, in-app project switching
- **M2 Linear Integration** — GraphQL client, issue/comment fetching, caching
- **M3 GitHub Integration** — REST client, PR/comment fetching, merge status
- **M4 TUI Enhancements** — status grouping, ticket/PR columns, detail modals, "Not Started" ghost rows
- **M5 Realtime Updates** — background polling loop, optional webhook receivers
- **M6 Polish** — tests, error surfaces, README

When starting a new session, read `ISSUES.md` first to know what's next. Mark issues `[x]` as they're completed. Add new issues inline as they emerge.

## Key External Resources

### Linear
- GraphQL API portal: https://linear.app/developers
- API & Webhooks docs: https://linear.app/docs/api-and-webhooks
- Webhook reference (signature verification, events, retry policy): https://linear.app/developers/webhooks
- Official SDK schema reference (TypeScript, use for field names): https://github.com/linear/linear/tree/master/packages/sdk

### GitHub
- REST API — Pull Requests: https://docs.github.com/en/rest/pulls/pulls
- REST API — Issue Comments: https://docs.github.com/en/rest/issues/comments
- Webhooks (setup, security, event types): https://docs.github.com/en/webhooks

### Python Libraries
- `gql` (GraphQL client for Linear): https://github.com/graphql-python/gql
- `PyGithub` (GitHub REST client): https://github.com/PyGithub/PyGithub
- `httpx` (async HTTP, used with gql): https://github.com/encode/httpx

### Testing
- Textual testing guide (Pilot, run_test, snapshot testing): https://textual.textualize.io/guide/testing/

## Architecture

For the full system design (components, data flow, workflows, entity relationships), see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
