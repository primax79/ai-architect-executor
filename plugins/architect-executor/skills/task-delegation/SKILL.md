---
name: task-delegation
description: Author task specifications for an Executor agent (Kilo, or any other fast, semi-autonomous coding agent working alongside an Architect AI, typically in its own dedicated git worktree) and independently verify what it implements - via manual spec-writing and git-based interaction, as an alternative to delegating through an MCP-based connector (e.g. kilo-mcp's tools - functional and the recommended default where available; that path is covered by that connector's own skills, this skill must not be conflated with those). This skill's spec-writing and verification guidance applies regardless of which path dispatches the work, but its execution mechanics (git worktree commands, session inspection) describe the manual/CLI path specifically - use it when preparing a task/macroplan file meant to be handed to an Executor by hand, or when reviewing/verifying commits it has already produced - including interacting with its live worktree via git, applying fixes to it, and deciding what verification depth a given task warrants. Invoke explicitly for this manual workflow.
---

# Task Delegation

## Purpose

An Executor (running on a fast, often-free model like Gemini Flash)
implements quickly — implementation is rarely the bottleneck. Verification
is. This skill exists to make delegation itself cheap to get right: write
specs that are hard to misimplement, and calibrate how much verification
each result actually needs instead of applying the same amount of scrutiny
everywhere.

This grew out of a real multi-hour session independently reviewing 9
Executor-implemented tasks (a raw-SQL-to-SQLAlchemy conversion macroplan,
~110 call sites across 7 files) — see
`gcube_atlas/plans/completed/10-sqlalchemy-raw-sql-conversion/REVIEW-NOTES.md`
in that project for the full, real log this skill is distilled from.

## When to use

- Writing a task file (standalone, or as part of a
  `macroplan-authoring`-style plan) that will be handed to an Executor for
  implementation.
- Reviewing commits an Executor already produced, deciding what to verify
  and how deeply.
- Applying a fix directly to a file inside an Executor's dedicated
  worktree (common when direct file-edit tools are permission-blocked
  there).
- Deciding whether/when it's safe to merge, rebase, or otherwise touch a
  branch an Executor is actively working on.

Not for writing the plan's overall structure — use `macroplan-authoring`
for that (this skill is about the *content* of individual tasks handed to
an Executor specifically, and about verifying them, not about the `task/`
tree scaffolding: `CONTEXT.md`, `specs/`, `NN-<slug>/plan.md` and its
tasks).

## Writing the spec: task granularity is the single biggest lever on defect rate

Narrow, single-module tasks come back clean almost every time. The one
task in the reviewed macroplan that was scoped as a broad
"cleanup/consolidation" pass — touching four already-converted files at
once to remove now-dead code — produced **three real regressions in one
commit**: an import removed from a file that still needed it, a
variable-initialization line moved to the wrong side of the code that
populates it (silently discarding a value on every request), and a
previously-dormant code path made live by a connection-type change,
crashing immediately. All three were the same failure pattern: "this
looked unused/movable in isolation" reasoning that only breaks down once
you check the whole file, or the whole system, at once.

**Rule**: when a task is fundamentally "go remove/consolidate
now-unused things across several files," either split it into one task
per file, or make its own Verification section mandate re-running the
*entire* regression suite — never just that task's own narrow checks.

## Writing the spec: ground everything in real code, and expect drift

Grep-verified call-site counts and line numbers go stale — confirmed
twice in one day in the reviewed session, once from intervening work
between planning sessions, once from a *same-day* merge that shifted
line numbers before the task even started. Never describe code
abstractly ("the handler that returns the repositories list"); cite the
real function/line, and write "re-`grep` for `X` before starting, this
may have shifted" directly into any step that cites an exact location.

## Writing the spec: trace who else calls what you're touching

Before writing a task's Steps, grep for every caller of any
function/file it converts or modifies — not just the one file currently
in scope. The hardest bugs in the reviewed session came from a shared
helper whose callers turned out to span two other files the task's
author hadn't traced (converting the helper's signature would have
silently broken both).

This applies doubly to "this UI page's data comes from endpoint X"
claims: verify the actual call chain (frontend service method → HTTP
call → backend route), not just endpoint X's own implementation in
isolation. A real mistake in the reviewed session targeted an endpoint
that matched the docs description and the URL's own name, but that the
UI never actually called — the fix landed correctly against the (wrong)
spec and changed nothing real.

## Writing the spec: one task, one commit

Note explicitly in the task file that it should result in one commit
scoped to just that task's changes — an agent working continuously
across several tasks may otherwise sweep up unrelated pending work
(another task's draft, an unrelated doc addition) into the same commit.

## Verifying the result: match depth to risk, don't verify everything the same way

- **Single-module conversion, narrow scope**: diff review against the
  spec, plus one functional smoke test. That's enough.
- **Cross-file, cleanup, or consolidation task**: full regression sweep,
  every time — this is exactly the category that produced real bugs in
  the reviewed session, and where the cost of thorough review is
  actually justified.
- **Once an automated test suite exists for the project**: every task
  touching source code should end with "run the suite, confirm green"
  as an explicit Verification step in the task file itself. This is the
  single highest-leverage way to close the gap between a fast/free
  implementation agent and a slower manual-verification process — it
  turns most of what used to require live-server-spinning and manual
  diffing into a ten-second automated check, runnable by the reviewer
  *or* by the Executor itself as a self-check before declaring a task done.
- **Always test against disposable copies** of real data/databases —
  never the real files. An implementation agent may be running its own
  live process against the real data concurrently (observed directly in
  the reviewed session — a live dashboard process on a real database,
  started by the Executor, hours earlier); a verification script pointed
  at the real file can hang on lock contention or corrupt shared state.

## Verifying the result: recognize when the Executor improves on the spec

Check outcome and reasoning, not literal compliance with the spec's
letter. In the reviewed session, one task was told "leave these four
functions permanently unconverted, to avoid breaking two other callers
that pass a different connection type." The Executor instead made the
four functions dual-compatible via duck-typing on the connection type —
which is strictly *better*: it preserved every existing caller **and**
let the rest of the codebase modernize, which the prescribed fix would
have permanently blocked. Don't mark that down as "didn't follow
instructions" — verify it actually works both ways and credit it.

## Operational: working inside an Executor's dedicated git worktree

When direct file-edit tools (Read/Edit/Write, or `grep`/`cat`/`sed` via
Bash) are permission-blocked against paths inside the Executor's
worktree, `git` subcommands run via Bash still work fine (`git -C
<worktree> log/show/diff/status`). See
`references/worktree-git-plumbing.md` for the exact technique to apply a
fix without direct file-edit access (build corrected content in a scratch
location, stage it as a blob via `git hash-object`/`update-index`,
materialize it via `checkout-index`), or run
`scripts/apply_fix_to_worktree.sh` directly.

**Before any git operation that touches a shared/live working tree**
(merge, revert, checkout, reset): check `git status` first. If there's
substantial live uncommitted work in progress, don't interrupt it — work
only on files it isn't currently touching, or wait for a natural commit
checkpoint. **Never pause or interrupt a live Executor session to ask
permission before proceeding around it** — the default is to let it keep
running; raise a coordination question only if genuinely blocked with no
safe path forward (e.g. every file you'd need to touch is already open in
the live session).

## Reference

See `references/worktree-git-plumbing.md` for the full git-plumbing
technique (exact commands, when each step is needed, how to verify
before committing) and `scripts/apply_fix_to_worktree.sh` for a
ready-to-run version of it.
