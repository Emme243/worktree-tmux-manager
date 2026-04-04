# Architecture

Below is a high-level design and architecture outline for your terminal dashboard app
that orchestrates worktrees, tmux sessions, integrated development tools (like your code editor, background code assistant,
and git UI), and external issue tracking via Linear and GitHub pull requests. This document describes the key components,
their relationships, the workflows between them, and sample user flows.

──────────────────────────────
## 1. OVERVIEW

• Purpose:
 – Provide a unified terminal interface (a TUI) that displays your current work items (tickets/issues) along with their
state—such as whether they have an associated worktree or tmux session—and highlights pending actions (for example, starting
coding on a ticket, checking unaddressed comments, etc.).
 – Streamline the process of transitioning from planning (Linear issues) to development (local git branches and worktrees)
to review (GitHub pull requests) by automating environment setup (e.g., spawning tmux sessions with integrated tools).

• Key Integrations:
 – Linear API: For retrieving ticket details, statuses, recommended branch names, etc.
 – GitHub API: For fetching pull request comments and merge statuses.
 – Local Git Environment: To check for worktrees and manage branches tied to a given ticket.
 – Tmux Session Manager: For launching and managing development sessions that bundle your editor, code assistant (claude
code), and git UI (lazygit).

──────────────────────────────
## 2. CORE COMPONENTS & MODULES

### A. Data Model / Domain Objects
 • Ticket/Issue Object
  – Unique identifier (from Linear)
  – Status (e.g., "Not started", "Worktree created", "Coding in progress", "Ready for PR")
  – Recommended branch name provided by Linear
  – Flags indicating whether a worktree exists, if a tmux session is active, and counts of unaddressed comments from both
Linear and GitHub

 • Git State Object
  – List of local branches and associated worktrees
  – Mapping between tickets and the corresponding branch/worktree

### B. External Integration Module
 • Communication with Linear:
  – Periodic or event-driven retrieval of issue statuses, recommended branch names, comment counts, etc.
 • Communication with GitHub:
  – Fetching pull request details (comments, merge status) that are linked to a ticket

### C. Git/Worktree Manager
 • Responsibilities include:
  – Checking the local git environment for existing branches and worktrees
  – Creating new worktrees or branches when a user starts working on an issue
  – Ensuring that branch naming conventions (possibly derived from Linear's recommendation) are followed

### D. Session Manager / Orchestrator
 • Manages the lifecycle of tmux sessions dedicated to a ticket
 • Spawns sessions with a preconfigured layout that might include:
  – A primary code editor window (e.g., neovim)
  – A background assistant window running your code generation/analysis tool
  – A git UI window for real-time repository status (lazygit or similar)
 • Coordinates the sequence of actions: from verifying that a worktree exists to launching tmux and updating ticket state

### E. User Interface Module (TUI Dashboard)
 • Built on your chosen text-based framework in Python
 • Displays a dashboard grouped by ticket progress status
 • Offers detailed views for each ticket, showing actionable items such as "Start worktree", "Launch tmux session", or
"Check comments"
 • Accepts keyboard commands to refresh data, select tickets, and trigger workflow actions

──────────────────────────────
## 3. DATA FLOW & WORKFLOW ORCHESTRATION

### A. On Startup (Initial Data Load)
 1. Load `~/.config/tt-tmux/config.toml`. If missing or has no projects configured, show the first-run
`ProjectSetupScreen` (directory-autocomplete input) so the user can set a repo path; save it and continue.
 2. If multiple projects are configured and no last-used project is recorded in
`~/.local/share/tt-tmux/state.json`, show the `ProjectPickerScreen`. Otherwise go directly to the last-used project.
 3. The TUI dashboard queries the External Integration Module for the latest ticket information from Linear and GitHub.
 4. It also inspects the local git environment via the Git/Worktree Manager to determine which tickets already have a
corresponding worktree or branch.
 5. All gathered data is mapped into your internal data model so that each ticket's status (e.g., "Not started" vs. "In
progress") can be accurately displayed.

### B. Dashboard View and Grouping
 • Tickets are grouped by their overall state:
  – "Not Started": No worktree exists; recommended branch is available but not yet checked out.
  – "Worktree Created": The ticket has an associated branch, but no active tmux session or coding activity yet.
  – "Coding in Progress": A worktree exists and a tmux session is running with the development tools launched.
  – "Ready for PR" or "Under Review": Tickets that are linked to GitHub pull requests awaiting review or merge.

### C. Ticket Detail Interaction & Action Triggers
 1. User selects a ticket from the dashboard:
  – The TUI displays detailed information (recommended branch, worktree status, unaddressed comment counts).
 2. Based on this detail view, the user can trigger one or more actions:
  • If no worktree exists:
   – Initiate a process to create a new branch (using Linear's recommendation) and set up the corresponding worktree.
  • If a worktree is present but no tmux session is active:
   – Launch a tmux session that arranges windows for editing, background code assistance, and git UI.
  • Regardless of state, the user can view linked pull request details to see if there are pending review comments.

### D. Workflow Transitions
 • The orchestrator (Session Manager) updates the ticket's status as actions occur:
  – "Not started" → "Worktree created" once a branch is checked out.
  – "Worktree created" → "Coding in progress" when a tmux session starts.
  – After coding, the user (or an automated check) can mark the ticket as "Ready for PR" and trigger GitHub integration to
open or update a pull request.
 • Any new comments from Linear or GitHub are polled periodically (or via webhook events if available), prompting status
refreshes in the dashboard.

──────────────────────────────
## 4. RELATIONSHIPS AMONG ENTITIES

• Central Role of the Ticket:
 – Every ticket (from Linear) is at the core. Its recommended branch name and status drive subsequent actions.

• Git Worktrees/Branches:
 – Serve as the local representation of a ticket's code space. They must reliably map back to the correct ticket so that
when you start working, your environment (tmux session) knows which ticket it belongs to.

• Tmux Sessions:
 – Act as an integrated development environment container. When launched for a ticket, they provide simultaneous access to
editing, coding assistance, and version control status.

• GitHub Pull Requests & Comments:
 – These represent the review stage. They are linked back to their respective tickets so that unaddressed comments (whether
from code reviews or automated checks) can be flagged in the dashboard.

──────────────────────────────
## 5. DESIGN CONSIDERATIONS & EXTENSIBILITY

• Separation of Concerns:
 – Keep UI rendering, external API interactions, local git operations, and session management in separate modules to ease
maintenance and future extension.

• Event-Driven Updates:
 – Consider using an event bus or polling mechanism so that changes (e.g., new comments on GitHub) trigger updates in the
TUI without manual refreshes.

• Error Handling & Logging:
 – Ensure robust error handling for API calls, git operations, and session launches. Log errors with sufficient detail to
troubleshoot integration issues.

• Configurability:
 – Allow users to customize tmux layouts, polling intervals, or even add new integrations (for example, additional code
analysis tools) without modifying core logic.

• Future Extensions:
 – Notifications for urgent updates (e.g., new review comments).
 – More granular state transitions with additional intermediate steps.
 – Integration hooks for custom scripts or workflows that a user might want to add over time.

──────────────────────────────
## 6. SAMPLE USER FLOW

Imagine your typical day as a developer using the app:

1. You launch the TUI dashboard. The system immediately fetches and displays:
  • A list of tickets from Linear (grouped by state: "Not started", "Worktree created", etc.)
  • For each ticket, details such as recommended branch names and counts for pending comments from both Linear and GitHub.

2. You see a ticket marked "Not started" that you want to work on:
  – You select it and view its detail panel.
  – The system suggests creating a new git worktree using the provided branch name.

3. With one command, the Git/Worktree Manager creates the branch and sets up the worktree locally.

4. Next, you trigger the Session Manager to launch a tmux session:
  – This spawns multiple windows: one for your code editor (neovim), another running your background code assistant (claude
code) for suggestions, and a third displaying real-time git status via lazygit.

5. As you work, any new comments on the associated GitHub pull request are periodically fetched:
  – The dashboard updates to show if there are now pending review items that require attention.

6. Once your changes are complete, you can mark the ticket's state as "Ready for PR" (or have an automated check in place),
which then prompts GitHub integration to update or open a new pull request.

──────────────────────────────
## 7. CONCLUSION

This architecture creates a seamless bridge between planning and development environments by:
 • Automating routine setup tasks (branch creation, tmux session launch)
 • Providing real-time feedback on review statuses
 • Allowing you to manage your workflow entirely from the terminal

By modularizing each responsibility—from data retrieval to environment management—you ensure that future changes (such as
adding more integrations or custom workflows) can be implemented with minimal disruption.

This design should serve as a solid blueprint for building your integrated TUI workflow. Feel free to iterate on these
components based on your specific needs and any emerging requirements during development.
