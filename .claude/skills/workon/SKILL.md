---
name: workon
description: >
  Full task orchestration: plan, implement, verify, QA, and deliver.
  Invoke with /workon <task description>.
disable-model-invocation: true
argument-hint: "<task description>"
---

# /workon — Task Workflow Orchestration

You are executing a structured workflow for the following task:

**Task:** $ARGUMENTS

Follow every phase below in order. Do not skip phases. If something goes wrong
at any point, STOP and return to Phase 1 to re-plan.

---

## Phase 0: Bootstrap

1. Read `tasks/lessons.md` if it exists — internalize all lessons before starting.
2. Read `ISSUES.md` for current project state and relevant context.
3. Create `tasks/` directory if it doesn't exist.

---

## Phase 1: Plan

**Enter plan mode.** Do not write any code yet.

1. Analyze the task: "$ARGUMENTS"
2. Use Explore subagents to investigate the codebase in parallel:
   - One subagent per area of investigation (e.g., "find all files related to X",
     "understand how Y works", "check docs for Z")
   - Keep the main context window clean — offload exploration
3. Write a detailed plan to `tasks/todo.md` using this format:

```markdown
# Task: <short title>

## Description
<1-2 sentence summary of what we're building/fixing>

## Analysis
<Key findings from exploration. What exists, what needs to change, why.>

## Plan
- [ ] Step 1: <concrete action>
- [ ] Step 2: <concrete action>
- [ ] ...

## Decisions
<Any architectural decisions made and why>

## Review
<filled in after completion>
```

4. **Check in with the user** before proceeding to Phase 2.
   - Present the plan summary
   - Ask: "Ready to proceed, or want to adjust?"
   - Wait for explicit confirmation

**Planning rules:**
- ANY task with 3+ steps or architectural decisions MUST be planned
- For trivial tasks (1-2 obvious steps), briefly state what you'll do and proceed
- Write specs detailed enough that there's no ambiguity during implementation

---

## Phase 2: Implement

Execute the plan from `tasks/todo.md` step by step.

1. **Mark each step in progress** as you start it (update `tasks/todo.md`)
2. **One concern at a time** — complete each step before starting the next
3. **Explain changes** — provide a high-level summary after each step
4. **Mark steps complete** — check off items in `tasks/todo.md` as you go

**Implementation principles:**
- **Simplicity first:** Make every change as simple as possible. Minimal code impact.
- **No laziness:** Find root causes. No temporary fixes. Senior developer standards.
- **Minimal impact:** Only touch what's necessary. Avoid introducing bugs.
- **Demand elegance (balanced):** For non-trivial changes, pause and ask yourself
  "is there a more elegant way?" If a fix feels hacky, step back and implement the
  elegant solution. Skip this for simple, obvious fixes — don't over-engineer.
- **Clean code:** Apply the `clean-code-principles` skill — follow SOLID, DRY, KISS,
  and YAGNI principles. Review your own code against these rules before moving on.

**Subagent strategy during implementation:**
- Use subagents for parallel research or analysis
- One task per subagent for focused execution
- For complex problems, throw more compute at it via subagents

**If something goes sideways:**
- STOP immediately — don't keep pushing
- Return to Phase 1 — re-plan with what you now know
- Update `tasks/todo.md` with the revised plan

---

## Phase 3: Verify

Never mark a task complete without proving it works.

1. **Run the test suite:** `uv run pytest`
2. **Run linting:** `uv run ruff check modules/ tests/ main.py`
3. **Run the specific tests** related to your changes
4. **Write/update tests** for new or changed behavior — apply the `python-testing-patterns`
   skill for pytest best practices (fixtures, parametrize, mocking, AAA pattern).
5. **If tests fail:** fix them autonomously. Read the errors, trace the cause, resolve
   it. Don't ask the user how — zero context switching required from them.
6. **Diff check:** When relevant, diff behavior between main branch and your changes
7. **Staff engineer test:** Ask yourself — "Would a staff engineer approve this?"
   - Is the code clean and well-structured?
   - Are edge cases handled?
   - Is there unnecessary complexity?
   - Are there any regressions?
8. **Challenge your own work** before presenting it

**If verification reveals problems:**
- Fix them directly — point at logs, errors, failing tests, then resolve them
- If the fix is non-trivial, return to Phase 1 to re-plan
- Go fix failing tests without being told how

---

## Phase 4: QA Handoff

Update `tasks/todo.md` with a `## Review` section summarizing what was implemented,
what tests were added/modified, and any deviations from the original plan.

Then output a **QA checklist** for the user:

```
## QA Checklist

1. [ ] <specific thing to test — include exact steps>
2. [ ] <specific thing to verify>
3. [ ] ...

Please test these items and let me know:
- "QA pass" → I'll commit and push
- Describe what failed → I'll fix it
```

**Checklist rules:**
- Focus on user-visible behavior and edge cases
- Each item has a clear pass/fail — no ambiguity
- Include exact steps (e.g., "run the app, press 'a', verify modal appears")
- Keep it short — only things that can't be verified programmatically
- Don't include things already covered by automated tests

---

## Phase 5: QA Loop

**Wait for user response.**

### If user confirms QA pass:
1. Stage all relevant changed files specifically (no `git add .` or `git add -A`)
2. Commit with a clear, conventional message describing the change
3. Push to the current branch
4. Report: commit hash, branch name, summary of what was pushed

### If user reports issues:
1. Acknowledge the specific issue
2. Return to **Phase 2** — implement the fix
3. Go through **Phase 3** — verify the fix
4. Go through **Phase 4** — output a new QA checklist (may be shorter)
5. Repeat this loop until QA passes → commit → push

---

## Self-Improvement Protocol

**After ANY correction from the user** (at any phase):

1. Identify the pattern — what went wrong and why
2. Append a lesson to `tasks/lessons.md`:

```markdown
### <Date> — <Short title>
**Trigger:** <What happened>
**Lesson:** <What to do differently>
**Rule:** <Concrete rule to follow going forward>
```

3. Apply the lesson immediately to the current task
4. These lessons are read at Phase 0 of every `/workon` invocation

---

## Quick Reference

| Situation | Action |
|-----------|--------|
| Non-trivial task (3+ steps) | Plan mode first (Phase 1) |
| Something breaks mid-implementation | STOP → re-plan |
| Need to explore code or research | Spawn an Explore subagent |
| User corrects you | Update `tasks/lessons.md` |
| Tests fail | Fix autonomously — don't ask how |
| Fix feels hacky | Step back, find the elegant solution |
| Trivial/obvious fix | Just do it, skip elegance review |
| Ready to present | QA checklist first, never just "it's done" |
| QA fails | Fix → verify → new QA checklist → repeat |
| QA passes | Commit and push |
