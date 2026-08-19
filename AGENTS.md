# AGENTS.md — ai-architect-executor

The generic, protocol-agnostic Architect/Executor pattern for delegating
work from an orchestrating AI to a worker AI — task discovery, isolation,
delegation, monitoring, verification, and a headless-worker behavioral
contract. No concrete tool names belong in this repo's skill prose; that's
what a *binding* (see below) is for. Full pitch: [`README.md`](README.md).
Design history and rationale for the split this repo came out of:
[`STATUS.md`](STATUS.md). Part of the `primax79/*` family — see the
workspace root's `AGENTS.md` (one level up) for the sibling-repo map.

## Layout

- `plugins/architect-side/` — `orchestration-methodology`,
  `delegation-roi-analysis`, `conflict-resolver`, `task-spec-authoring`,
  `task-delegation` skills.
- `plugins/executor-side/` — `headless-executor-contract` skill.
- `plugins/shared/` — `interactive-role-setup` skill.
- `scripts/generate_binding.py` — generates a **binding** (a concrete tool
  fork of a protocol-agnostic skill here, e.g. naming real MCP tools) into
  a downstream repo.
- `scripts/regenerate_generic_skills.py` / `scripts/generate_skill_indices.py`
  — regeneration and index maintenance for this repo's own skills.

## Mandatory rules

- **Stay protocol-agnostic.** Nothing under `plugins/` may name a concrete
  tool, MCP function, or product (`kilo_implement`, etc.). If a change
  needs a concrete name to make sense, it belongs in a binding (currently
  `kilo-mcp`), not here.
- **This repo is upstream of `kilo-mcp`'s bound skills.** `kilo-mcp`
  generates `orchestration-methodology`, `headless-executor-contract`,
  `conflict-resolver`, and `delegation-roi-analysis` from this repo's
  `SKILL.template.md` sources (via `scripts/generate_binding.py` here,
  `scripts/regenerate_bound_skills.py` there). If you edit one of those
  four skills' *methodology* (not binding-specific detail), the change
  needs to flow to `kilo-mcp` too — check whether `kilo-mcp/bindings/*.json`
  needs a matching update and whether `regenerate_bound_skills.py` needs to
  be re-run there. `task-spec-authoring`, `task-delegation`, and
  `interactive-role-setup` have no bound counterpart — edit them freely,
  nothing downstream to keep in sync.
- **Skill manifest.** New/changed skills need valid YAML frontmatter
  (`name`, `description`) in `SKILL.md` — Kilo's loader silently skips a
  skill without it.
- **Regenerate indices.** After adding, removing, or renaming a skill,
  run `python3 scripts/generate_skill_indices.py` and commit the updated
  `index.json` files alongside the change.
- **`task-spec-authoring`/`orchestration-methodology` reference an external
  convention** (`agentic-coding-kit`'s `macroplan-authoring` `tasks/` tree)
  without vendoring it — don't duplicate that convention here; link to it.
  See `plugins/architect-side/dependencies.json` for the informational,
  non-enforced record of that dependency.

## Before committing

Only when explicitly asked to commit: check `git status`/`git diff` for
scope and secrets, and if a template skill listed above changed, flag to
the user that `kilo-mcp`'s bound copy may now be stale.
