# ai-architect-executor

The generic, protocol-agnostic **Architect/Executor** pattern for
delegating work from an orchestrating AI to a worker AI: task discovery,
isolation, delegation, monitoring, verification, and a headless-worker
behavioral contract. Not tied to Claude, not tied to Kilo, not tied to
MCP - those are all one possible *binding* of this pattern, not the
pattern itself.

The vocabulary ("Architect" / "Executor") wasn't invented for this repo -
it was already in use in `kilo-mcp`'s skill prose (its `pyproject.toml`
describes it as "the architect/executor pattern") before anyone framed it
as a reusable, protocol-agnostic abstraction. See `STATUS.md` for the full
history and decision log of the split this repo came out of.

## Why this exists

An orchestrating AI (the **Architect**) is good at reasoning, design, and
review, but running a large implementation task through it directly is
slow and token-heavy. A fast, semi-autonomous coding agent (the
**Executor**) is good at implementation but needs a spec and doesn't
review its own work critically. Splitting the two roles - and being
disciplined about *how* the split works (isolate before delegating, verify
by actually running the result rather than trusting a report, calibrate
monitoring to task risk) - is the actual leverage. This repo is that
discipline, written down once instead of re-derived per project or
rediscovered the hard way per session.

## What's in this repo - three plugins, install the side(s) you need

| Plugin | Skill | Covers |
| --- | --- | --- |
| `architect-side` | `orchestration-methodology` | The 6-phase methodology: discovery, isolation, delegation, monitoring & intervention, verification & review, closure & telemetry. |
| `architect-side` | `delegation-roi-analysis` | Evaluating whether delegation is paying off - cost vs. inline-generation estimate, defect-pattern review, feedback-loop proposals. |
| `architect-side` | `conflict-resolver` | Resolving merge conflicts between parallel Executor outputs. |
| `architect-side` | `task-spec-authoring` | Writing Executor task specs and calibrating verification depth - applies regardless of dispatch path. |
| `architect-side` | `task-delegation` | The **manual** (non-protocol) delegation path specifically: git-worktree mechanics for handing off a task and interacting with its live worktree. |
| `executor-side` | `headless-executor-contract` | The Executor-side behavioral contract for running headless: zero interactivity, `focus_files`, mandatory Final Report, fail fast, scope discipline. |
| `shared` | `interactive-role-setup` | Maps the kit's abstract role profiles (`deep-reasoning`/`orchestration`/`bulk-execution`/`exploration`) to whatever models/hosts you actually have. Useful to either side. |

All seven skills are protocol-agnostic by design - no concrete tool names.
The fully concrete version of four of them (`orchestration-methodology`,
`headless-executor-contract`, `conflict-resolver`, `delegation-roi-analysis`),
naming actual MCP tools, is *generated* from this repo's templates in
[`kilo-mcp`](https://github.com/primax79/kilo-mcp) - see
`scripts/generate_binding.py` here and `scripts/regenerate_bound_skills.py`
there. `task-spec-authoring`, `task-delegation`, and `interactive-role-setup`
have no binding-specific counterpart - they don't need one.

## Relationship with the other repos in this family

- **[`kilo-mcp`](https://github.com/primax79/kilo-mcp)** - depends on this
  repo at build time: its skills are *generated* from this repo's
  `SKILL.template.md` sources plus its own binding maps (`bindings/*.json`,
  see `scripts/regenerate_bound_skills.py` there), not hand-duplicated.
  Install `kilo-mcp`'s skills if you're driving Kilo Code via MCP - they
  carry the real tool names. Install this repo's skills for a different
  binding, or the protocol-agnostic form. **Never install both**: same
  methodology, same activation triggers, guaranteed to compete for the
  same description match.
- **[`agentic-coding-kit`](https://github.com/primax79/agentic-coding-kit)** -
  one real dependency in this direction: several skills here
  (`task-spec-authoring`, `orchestration-methodology`) reference the
  `tasks/` tree convention owned by that repo's `macroplan-authoring` skill
  (`common-tools` plugin) for multi-session/delegated work. Install that
  plugin alongside this one if you use macroplan-style task trees - this
  repo does not vendor or duplicate that convention (see
  `plugins/architect-side/dependencies.json` for the machine-readable
  record; informational only, neither tool's installer enforces it today).
  Everything else about the relationship is as before: its `agent-tooling-meta` plugin is about
  *configuring* Kilo/Claude as installed tools, this repo is about
  *delegating work* between them - see that repo's
  [`docs/01-concepts.md`](https://github.com/primax79/agentic-coding-kit/blob/main/docs/01-concepts.md)
  for general Claude Code/Kilo Code plugin & marketplace mechanics, not
  repeated here.
- **[`gcube-ai-toolkit`](https://github.com/primax79/gcube-ai-toolkit)** -
  no dependency; disjoint content (gCube/D4Science-specific vs. generic).

## Install

Same mechanics as the rest of this family -
[`agentic-coding-kit`'s docs](https://github.com/primax79/agentic-coding-kit/tree/main/docs)
cover the concepts/authoring/distribution detail in full; short version:

**Claude Code:**

```bash
claude plugin marketplace add https://github.com/primax79/ai-architect-executor.git
/plugin install architect-side   # or executor-side, or shared - pick what you need
```

**Kilo Code**, via `kilo-plugin-manager` (pick the plugin(s) you need - `architect-side`,
`executor-side`, `shared`, or several):

```bash
python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py add https://github.com/primax79/ai-architect-executor.git --name ai-architect-executor
python3 ~/.kilo/skills/kilo-plugin-manager/scripts/plugin_manager.py install architect-side@ai-architect-executor
```

or Kilo's native Skill URLs (no extra tooling, one URL per plugin):

```text
https://raw.githubusercontent.com/primax79/ai-architect-executor/main/plugins/architect-side/skills/
https://raw.githubusercontent.com/primax79/ai-architect-executor/main/plugins/executor-side/skills/
https://raw.githubusercontent.com/primax79/ai-architect-executor/main/plugins/shared/skills/
```

Regenerate `index.json` after any skill change: `python3 scripts/generate_skill_indices.py`.

## License

[MIT](LICENSE)
