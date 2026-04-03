# ISSUES.md — Local Issue Tracker

This file is the source of truth for what needs to be built to achieve the full vision described in `CLAUDE.md`.
Work through issues milestone by milestone. Mark items `[x]` when done. Add new issues as they emerge.

---

## Milestone 1 — Foundation

> Config system and domain models. Everything else depends on this.

- [x] **M1-01 · Config system** — Replace hardcoded `~/projects/turntable` with a user-editable config file (`~/.config/tt-tmux/config.toml` or `.tt-tmux.toml` in the repo root). Config must hold: `repo_path`, `linear_api_key`, `github_token`, `github_repo` (owner/repo slug), `linear_team_id`. Load at startup; show clear error if missing required keys.

- [x] **M1-02 · Domain models — Ticket** — Create `modules/linear/models.py` with a `Ticket` dataclass: `id`, `identifier` (e.g. `ENG-123`), `title`, `status` (enum: `NotStarted | InProgress | InReview | Done | Cancelled`), `branch_name` (Linear's suggested branch), `url`, `assignee`, `updated_at`, `unread_comment_count`. Add a `TicketWorkflowState` enum mapping to dashboard grouping.

- [x] **M1-03 · Domain models — PullRequest & Comment** — Create `modules/github/models.py` with `PullRequest` (`number`, `title`, `state`, `url`, `head_branch`, `base_branch`, `merged`, `draft`, `unread_comment_count`, `updated_at`) and `Comment` (`id`, `body`, `author`, `created_at`, `is_read`).

- [x] **M1-04 · Branch ↔ Ticket mapping** — A `WorktreeInfo` needs to know its associated Linear ticket (if any). Strategy: match `WorktreeInfo.branch` against `Ticket.branch_name`. Implement `resolve_ticket(worktree: WorktreeInfo, tickets: list[Ticket]) -> Ticket | None` in a new `modules/core/mapping.py`. Also store the resolved mapping in an in-memory registry so it doesn't recompute on every render.

- [x] **M1-05 · Worktree ↔ PR mapping** — Match `WorktreeInfo.branch` against `PullRequest.head_branch`. Implement `resolve_pr(worktree: WorktreeInfo, prs: list[PullRequest]) -> PullRequest | None` alongside M1-04.

---

## Milestone 1-B — First-Run & Multi-Project UX

> Guided setup on first launch, filesystem-aware path input, and multi-project support. Transforms the app from a single-repo tool into a project launcher. Work these in order — each issue unblocks the next.

- [x] **M1B-01 · Config write support** — Add `save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None` to `modules/core/config.py`. Add `tomli-w` to `pyproject.toml` runtime deps. Implementation: create parent dirs (`path.parent.mkdir(parents=True, exist_ok=True)`), write to a `.tmp` sibling file, then `rename()` for atomic replacement. Tests in `tests/unit/core/test_config.py`: verify file is written, `repo_path` round-trips, atomic write leaves no tmp file on success.

- [x] **M1B-02 · DirectoryInput widget** — New `modules/widgets/directory_input.py`. A composed widget (Label + Input + AutoComplete) that provides filesystem tab-completion for directory paths. The `AutoComplete` provider reads the current input value, expands `~`, and lists immediate subdirectories as suggestions. Selecting a suggestion appends it. Supports absolute paths and `~`-prefixed paths. Tests in `tests/unit/widgets/test_directory_input.py`: suggestion list contents, `~` expansion, no suggestions for non-existent prefix.

- [x] **M1B-03 · Project setup screen** — New `modules/screens/project_setup.py`. `ProjectSetupScreen(mode: Literal["first_run", "add"])`: shown on first launch or when adding a new project. Contains `DirectoryInput` (M1B-02), inline status text, and a confirm button. On confirm: validate path exists (`os.path.isdir`) and is a git repo (`is_git_repo` async) — show inline error text if either fails, do not dismiss. On success: call `save_config()` (M1B-01) and `dismiss(chosen_path)`. Keys: `Enter` confirms, `Escape` exits app in `first_run` mode or dismisses with `None` in `add` mode. Tests cover: renders correctly, inline error on bad path, inline error on non-git dir, success dismisses with path.

- [x] **M1B-04 · Wire first-run into app startup** — Update `modules/app.py`: when `ConfigError` is caught and the cause is a missing file or missing `repo_path`, push `ProjectSetupScreen(mode="first_run")` instead of notify+exit. On dismiss with a path, continue the normal validation+load flow. On dismiss with `None` (user escaped), exit cleanly. Keep the existing notify+exit for `ConfigError` caused by invalid TOML syntax (not a first-run scenario). Update `tests/unit/test_app.py` accordingly.

- [x] **M1B-05 · Multi-project config schema** — Add `ProjectConfig(path: Path, name: str)` dataclass to `modules/core/config.py`. `name` defaults to `path.name` (the directory basename). Update `AppConfig`: add `projects: list[ProjectConfig] = field(default_factory=list)`. Migration in `load_config`: if `repo_path` key is present (old single-project format), synthesise a one-element `projects` list from it — do not break existing configs. `save_config` always writes the new `[[projects]]` array format. Tests: old single-`repo_path` config loads as one project, full multi-project round-trip, `name` defaults to directory basename.

- [x] **M1B-06 · Project picker screen** — New `modules/screens/project_picker.py`. `ProjectPickerScreen`: shown on startup when `len(config.projects) > 1` and no last-used project is recorded (see M1B-07). Displays a `VimDataTable` listing project name + path. Keys: `Enter` opens selected project's worktree list (dismiss with chosen `ProjectConfig`), `a` pushes `ProjectSetupScreen(mode="add")` and appends the result to config, `d` deletes selected project with a confirm modal, `Escape` exits app. Tests: renders project list, `Enter` dismisses with correct project, `a` adds a project, `d` removes with confirm.

- [x] **M1B-07 · Last-used project persistence** — New `modules/core/state.py` with `AppState(last_project_path: Path | None)`, `load_state() -> AppState`, and `save_state(state: AppState) -> None`. State file: `~/.local/share/tt-tmux/state.json` (create parent dirs on write). Startup logic in `app.py`: if one project → go straight to worktree list; if multiple projects and `last_project_path` matches a configured project → go straight to that worktree list (skip picker); otherwise → show `ProjectPickerScreen`. Save `last_project_path` whenever a project is opened. Tests: round-trip JSON, missing file returns `AppState(last_project_path=None)`, stale path (removed project) falls back to picker.

- [ ] **M1B-08 · In-app project switching** — Add `p` keybinding to `WorktreeListScreen` (`Binding("p", "switch_project", "Switch project")`). Action pushes `ProjectPickerScreen` as a modal (via `push_screen`). On dismiss with a `ProjectConfig`, reload the screen for the new project (update `self.repo_dir`, re-run data load, update title). Also calls `save_state` to update last-used project. Tests: `p` opens picker, dismissing with a project updates `repo_dir` and triggers reload.

---

## Milestone 2 — Linear Integration

> Fetch tickets and comments from Linear's GraphQL API.
> Docs: https://linear.app/developers | https://linear.app/docs/api-and-webhooks
> Schema: https://github.com/linear/linear/tree/master/packages/sdk
> Python GraphQL client: https://github.com/graphql-python/gql

- [ ] **M2-01 · Linear GraphQL client** — Create `modules/linear/client.py` using the `gql` library with `httpx` transport. Authenticate via Bearer token (`Authorization: Bearer {api_key}`). Implement `LinearClient` class with async methods. Add `gql[httpx]` and `httpx` to `pyproject.toml` runtime deps.

- [ ] **M2-02 · Fetch assigned issues** — Implement `LinearClient.fetch_my_issues(team_id: str) -> list[Ticket]`. GraphQL query should fetch: `id`, `identifier`, `title`, `state { name, type }`, `branchName`, `url`, `assignee { name }`, `updatedAt`, `comments { totalCount }`. Filter to issues assigned to the authenticated user and in active states (not `cancelled`/`completed`).

- [ ] **M2-03 · Fetch issue comments** — Implement `LinearClient.fetch_issue_comments(issue_id: str) -> list[Comment]`. Use the `issue(id:) { comments { nodes { id, body, createdAt, user { name } } } }` query. Mark comments as read/unread by comparing `updatedAt` against a local timestamp store (see M5-01).

- [ ] **M2-04 · Fetch a single issue by branch name** — Implement `LinearClient.fetch_issue_by_branch(branch: str) -> Ticket | None`. Use `issueSearch` or filter by `branchName` field. Useful when creating a worktree to auto-link to Linear ticket.

- [ ] **M2-05 · Linear data cache** — Store fetched tickets in a simple in-memory `LinearCache` (a dataclass holding `list[Ticket]` + `last_fetched: datetime`). Do not hit the API if last fetch was < N seconds ago (configurable, default 30s). Cache invalidated on webhook events (M5-02).

---

## Milestone 3 — GitHub Integration

> Fetch PR and comment data from GitHub REST API.
> Docs: https://docs.github.com/en/rest/pulls/pulls | https://docs.github.com/en/rest/issues/comments
> Python SDK: https://github.com/PyGithub/PyGithub

- [ ] **M3-01 · GitHub REST client** — Create `modules/github/client.py` using `PyGithub`. Authenticate with personal access token. Implement `GitHubClient` class wrapping a `github.Github` instance. Add `PyGithub` to `pyproject.toml`. Expose `async`-friendly wrappers using `asyncio.to_thread()` (PyGithub is synchronous).

- [ ] **M3-02 · Fetch open PRs** — Implement `GitHubClient.fetch_open_prs() -> list[PullRequest]`. Use `repo.get_pulls(state="open")`. Map PyGithub `PullRequest` objects to our domain `PullRequest` dataclass.

- [ ] **M3-03 · Fetch PR comments** — Implement `GitHubClient.fetch_pr_comments(pr_number: int) -> list[Comment]`. Use `repo.get_pull(pr_number).get_issue_comments()` (general comments) and `.get_review_comments()` (inline diff comments). Merge and sort by `created_at`.

- [ ] **M3-04 · Check PR merge status** — Implement `GitHubClient.get_pr_merge_status(pr_number: int) -> str`. Returns one of: `"open"`, `"merged"`, `"closed"`, `"draft"`. Handle the null-mergeable case (retry once after 1s).

- [ ] **M3-05 · GitHub data cache** — Mirror of M2-05 for GitHub data. `GitHubCache` with TTL and webhook-based invalidation.

---

## Milestone 4 — TUI Enhancements

> New screens and widgets to surface ticket data in the dashboard.

- [ ] **M4-01 · Status grouping in worktree list** — Extend `WorktreeListScreen` to group rows by workflow state. Groups (in order): `Coding in Progress` → `Worktree Created` → `Not Started` (Linear issues without worktree) → `Under Review` (has open PR). Add group header rows (non-selectable, styled differently). Preserve vim navigation across groups.

- [ ] **M4-02 · Ticket column in worktree table** — Add `Ticket` column to the main table showing `ENG-123` identifier (or `—` if unmapped). Show in cyan/blue color. Selecting this column or pressing `t` opens the ticket detail panel (M4-04).

- [ ] **M4-03 · PR column in worktree table** — Add `PR` column showing PR number + status emoji (`⬤ open`, `✓ merged`, `⬤ draft`). Pressing `p` opens the PR detail panel (M4-05).

- [ ] **M4-04 · Ticket detail modal** — New `modules/modals/ticket_detail.py`. Shows: identifier, title, status, assignee, Linear URL, comment count (unread highlighted). Lists recent comments. Keyboard: `o` opens Linear URL in browser, `Escape` dismisses.

- [ ] **M4-05 · PR detail modal** — New `modules/modals/pr_detail.py`. Shows: PR title, number, state, base/head branch, GitHub URL, review comment count. Lists PR comments (general + inline). Keyboard: `o` opens GitHub URL in browser, `Escape` dismisses.

- [ ] **M4-06 · "Not Started" ticket rows** — Show Linear tickets that have no local worktree as ghost rows in the table (grayed out). Pressing `Enter` on these starts the worktree creation flow (M4-07), pre-filling the branch name from `Ticket.branch_name`.

- [ ] **M4-07 · Pre-fill branch name from Linear ticket** — When creating a worktree (existing `AddWorktreeModal`), if a Linear ticket is selected or matched, pre-populate the branch input with `Ticket.branch_name`. This links the worktree to the ticket automatically.

- [ ] **M4-08 · Unread comment badges** — Show unread comment count as a badge on ticket/PR columns. Badge style: `[3]` in yellow if > 0. Mark comments as read when the detail modal is opened.

---

## Milestone 5 — Realtime Updates

> Keep the dashboard fresh without manual `r` refresh.
> Linear webhooks: https://linear.app/developers/webhooks
> GitHub webhooks: https://docs.github.com/en/webhooks

- [ ] **M5-01 · Read-state persistence** — Store "last seen" timestamps per issue/PR in a local JSON file (`~/.local/share/tt-tmux/read_state.json`). Used by comment unread logic (M2-03, M3-03) and to persist across restarts.

- [ ] **M5-02 · Background polling loop** — Add a `BackgroundPoller` worker in `modules/core/poller.py` using `asyncio` periodic tasks. Polls Linear and GitHub every N seconds (configurable, default 60s). Posts a `DataRefreshed` message to the app when new data arrives. Only polls when the app is in the foreground (skip if `app.is_suspended`).

- [ ] **M5-03 · Linear webhook receiver (optional)** — For users who want real-time updates: a lightweight ASGI webhook endpoint (`modules/webhooks/linear_handler.py`) that verifies the `Linear-Signature` HMAC-SHA256 header (timing-safe, raw body bytes), validates `webhookTimestamp` within 60s, then posts invalidation events to the poller. Deploy with `uvicorn` or expose via `ngrok` in dev. This is optional — polling (M5-02) is the default.

- [ ] **M5-04 · GitHub webhook receiver (optional)** — Mirror of M5-03 for GitHub. Validate webhook secret, parse `pull_request` and `issue_comment` events, invalidate cache. Optional companion to M5-02.

- [ ] **M5-05 · Auto-refresh on tmux return** — When the user returns from a tmux session (after `app.suspend()` completes), trigger an immediate background refresh of git worktree statuses and Linear/GitHub data.

---

## Milestone 6 — Polish & Testing

- [ ] **M6-01 · Unit tests: Linear client** — Mock `gql` transport; test query construction, response parsing, error handling, and caching TTL logic.

- [ ] **M6-02 · Unit tests: GitHub client** — Mock `PyGithub`; test PR fetching, comment merging, merge status retry logic.

- [ ] **M6-03 · Unit tests: mapping** — Test `resolve_ticket()` and `resolve_pr()` with various branch name formats (kebab-case, slashes, Linear prefix).

- [ ] **M6-04 · Integration test: full startup flow** — Smoke test that app starts, loads config, fetches (mocked) Linear/GitHub data, and renders the worktree list with ticket columns.

- [ ] **M6-05 · Error surfaces in TUI** — Show non-fatal API errors as dismissible toast notifications (Textual's `notify()`), not crashes. Fatal config errors (missing token) should show a dedicated `ConfigErrorScreen` instead of the worktree list.

- [ ] **M6-06 · README update** — Document setup: config file format, Linear API key generation, GitHub token scopes required (`repo`, `read:user`), and optional webhook setup.

---

## Backlog (Unscheduled)

- ~~**B-01 · Multiple repo support**~~ — Promoted to Milestone 1-B (M1B-05 + M1B-06).
- [ ] **B-02 · Mark issue as "In Progress" on worktree create** — Call Linear `issueUpdate` mutation to move ticket to "In Progress" when a worktree is created.
- [ ] **B-03 · Open PR from TUI** — From the PR detail modal, add action to open a draft PR on GitHub using `repo.create_pull()`.
- [ ] **B-04 · Cycle through comments with `n`/`N`** — Vim-style comment navigation in detail modals.
- [ ] **B-05 · Configurable tmux layout** — Allow users to define window presets in config (editor command, additional windows, working directory overrides).

---

## Notes

- `tomllib` (stdlib, Python 3.11+) is read-only. `tomli-w` (runtime dep, added in M1B-01) is the write companion — both use the same dict format so round-tripping is lossless.
- State file (`~/.local/share/tt-tmux/state.json`) is separate from config (`~/.config/tt-tmux/config.toml`) by design: config is user-editable/version-controllable, state is machine-local runtime data.
- Linear has no official Python SDK. Use `gql[httpx]` (GraphQL client) + direct queries. The TypeScript SDK schema at https://github.com/linear/linear/tree/master/packages/sdk is the best reference for field names.
- GitHub's PR `mergeable` field is computed async — always retry once on `null`.
- Linear webhooks require a public HTTPS URL; for local dev use `ngrok` or skip webhooks and rely on polling.
- Linear webhook timeout is 5s — respond immediately with 200, process async.
- GitHub webhook delivery history is only 3 days; implement local event logging if needed.
- Linear HMAC verification must use raw request body bytes (not re-serialized JSON).
