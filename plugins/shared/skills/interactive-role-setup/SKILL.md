---
name: interactive-role-setup
description: "Interactively maps the kit's four abstract role profiles (deep-reasoning, orchestration, bulk-execution, exploration) to whatever models/hosts the operator actually has available, persists the mapping to roles.toml, and verifies it against the live host config rather than trusting it blindly. Use when setting up role-to-model mapping for the first time, or re-checking whether an existing mapping still holds (host settings drift, new models, tightened allowlists)."
---

# Interactive role setup

The Architect/Executor kit (`ai-architect-executor` + concrete bindings like `kilo-mcp`)
never hardcodes a model inside a skill. A `model: opus` written into a protocol-agnostic
skill is a vendor dependency placed in the artifact least entitled to carry one — and the
same skills load under Kilo too (via Skill URLs), where an Anthropic model alias means
nothing. The model choice belongs to whoever installs the kit, not to the pattern.

What the kit's skills carry instead is a **role profile** — a declaration of how much a
piece of work tolerates being done poorly, not which model should do it:

| Profile | Meaning | Examples in the kit |
|---|---|---|
| `deep-reasoning` | Silent failures — nothing downstream catches them | Spec authoring, substantial diff review, merge-conflict judgment calls |
| `orchestration` | Loud, immediate failures | Dispatch, polling, bookkeeping, close-out |
| `bulk-execution` | High-volume implementation under a written spec | What gets delegated to the Executor |
| `exploration` | High volume, low judgment, read-only | RAG search, codebase Q&A |

This skill is the missing link: it discovers what's actually reachable, ranks it into
capability tiers with the evidence recorded, proposes a full four-profile mapping with a
one-line justification each, and only then asks the operator to confirm or correct —
writing the result to a config file the rest of the kit can read. The operator's job is
reviewing a proposal, not producing one from a blank slate.

## What this skill does NOT do — an explicit constraint, not an oversight

**It never writes another tool's configuration.** Not `~/.claude/settings.json`, not a
subagent's frontmatter, not a `.kilo/agent/*.md` file. Two structural reasons:

- If this skill could write those files, every schema change in those tools becomes a bug
  here.
- Every host already has its own confirmation/permission/diff flow. Reimplementing that
  here would just be a worse copy.

**Hand off by intent, not by patch.** This skill ends by emitting a natural-language
request the operator carries to the relevant host's own chat — e.g. "configure subagent X
to use the high tier at xhigh effort" — and that host applies it in its own current
schema. A generated JSON blob goes stale the moment the schema changes; a stated intent
does not. Same reasoning as why the kit calls `kilo_list_models` instead of memorizing
model IDs: don't hardcode what can be queried.

**It never runs unattended.** This is an interactive setup flow, not a daemon. It only
starts when the operator explicitly invokes it.

## Config file: `roles.toml`

Global, one mapping per machine/operator:

```
~/.config/ai-architect-executor/roles.toml
```

```toml
[roles.deep-reasoning]
host = "claude-code"
model = "opus"
effort = "high"
basis = "operator-stated"  # optional — see "Ranking" in Guided flow; omitted below on purpose
last_verified = "2026-08-06"

[roles.orchestration]
host = "claude-code"
model = "sonnet"
effort = "medium"
last_verified = "2026-08-06"

[roles.bulk-execution]
host = "kilo"
model = "google/gemini-3.5-flash"
last_verified = "2026-08-06"

[roles.exploration]
host = "kilo"
model = "google/gemini-3.5-flash"
last_verified = "2026-08-06"
```

This is a new file, not an extension of `kilo-mcp.toml`'s `delegation_policy`. That file
is scoped to one MCP server process (env vars prefixed `KILO_MCP_*`, read only by the
Python server); role mapping is read by markdown-based skills across the whole kit,
independent of which binding is installed. Reusing it would couple a general-purpose
setting to one specific server's config surface.

Project-local overrides are an explicit non-goal for now — the default is global. Revisit
only if a real case for per-project differentiation shows up.

## Guided flow

The skill performs the capability analysis itself; the operator reviews and corrects a
proposal instead of producing one from a blank slate. Confirmation still happens per
profile at the end — what changes is what's being confirmed.

The hard constraint that shapes every step below: **the kit carries no hardcoded model
lineup in its logic.** The ranking cannot be a lookup table — it has to be derived at
runtime from evidence, and the evidence has to be recorded so a wrong ranking is visible
rather than silent.

### 1. Discovery

Enumerate what's *reachable*, not just what's currently configured — the operator is
usually running inside one of the hosts being mapped, so read before asking:

- **Kilo**: call its live model-listing tool unfiltered. The currently configured default
  is one entry, not the candidate set.
- **Claude Code**: the running session's own model (visible directly, no file read
  needed), `~/.claude/settings.json`'s `model` key, `CLAUDE_CODE_SUBAGENT_MODEL` in the
  environment, and — where readable — the set of models the plan/organization actually
  permits. An org-managed seat with a restricted allowlist has a different candidate set
  than a personal plan.
- Any other host reachable in the environment (e.g. `~/.config/kilo/kilo.jsonc`'s
  `model`/`small_model`/`agent.*.model` keys, if that host is in play).

Record, per candidate, whatever metadata the host actually returns — identifier,
provider, context window, cost, tier naming, effort support. Never invent a field the
host didn't supply, and never substitute a memorized model lineup for this step (see
"Ranking" for the one narrow, explicitly fallible exception).

A host that can't be enumerated isn't silently skipped — record which host and why; it
resurfaces at gap reporting.

### 2. Ranking

Sort each host's candidates into capability tiers, separately per host — a Kilo model and
a Claude Code model are usually not competing for the same profile, so there's no single
cross-host scale to place them on. Use whichever evidence is actually available, in this
order of preference, and **record which one was used** as the role's `basis`:

1. `host-metadata` — explicit tier fields, cost, or context window returned by the host
   itself. Cost ordering is a reasonable proxy for capability ordering within one provider
   when nothing more explicit is available.
2. `provider-tier-naming` — the host's own tier vocabulary, when it exposes one.
3. `model-self-knowledge` — the executing model's own knowledge of the lineup it's part
   of. Usable, but explicitly fallible and version-dependent; say so out loud whenever a
   ranking rests on it.
4. `operator-stated` — asking the operator directly. The correct fallback when the above
   are absent or contradictory, not a failure state.

An unexplained tier assignment is a defect, not a shortcut: the point of recording the
basis is that the operator can see *why* a model landed where it did and correct a wrong
premise instead of a wrong answer.

### 3. Mapping

Propose all four profiles in one pass — host + model + effort (where the host supports
it) + a one-line justification grounded in error tolerance, not in model marketing:

- `deep-reasoning` → the highest tier reachable on its host. Failures here are silent;
  capability is bought regardless of how easy a given task looks.
- `orchestration` → a mid tier. Failures here are loud and immediate, and this is also
  where most turns go — it dominates consumption more than it dominates risk.
- `bulk-execution` → whatever the Executor host offers at high throughput; cost matters
  most here because volume is highest.
- `exploration` → the lowest adequate tier — read-only, high volume, errors obvious on
  sight.

Effort is a second axis, not a tie-break: propose it explicitly wherever the host supports
it, following this rule — a high tier at reduced effort is usually worse than a mid tier
at full effort, because it pays for the expensive model while discarding the depth it was
chosen for.

### 4. Gap reporting

Partial or degenerate discovery gets named, not papered over:

- **Fewer distinct tiers than profiles** — say plainly that some roles collapse onto the
  same model, and what that costs, rather than presenting a mapping that looks
  differentiated but isn't.
- **No low-tier option** — `exploration`/`bulk-execution` will run expensive; worth
  knowing before it shows up as consumption.
- **No high-tier option** — `deep-reasoning` is being done on something that doesn't
  really suit it. The single most consequential gap, because its failures are silent by
  definition.
- **A host that couldn't be enumerated** — state which, and that any profile mapped
  through it rests on incomplete discovery.

### 5. Confirm, then persist

Present the full proposal as a table — profile, host, model, effort, justification,
ranking basis — then run the per-profile confirm-or-correct step: ask whether each row is
what the operator wants, or something else. Never skip this even when discovery and
ranking were clean: current/discovered config is evidence of what's *available*, not of
what the operator *wants* for a given profile — a cheap default configured for cost
reasons is not evidence they want it for `deep-reasoning`.

On confirmation, write `roles.toml` in the existing shape plus the optional `basis` field
from step 2 (see "Config file" above). Nothing else about the schema changes.

## Verification

Setup is only as good as its verification — an operator hands intent to a host, the host
does something, and this skill has to check what actually happened, not assume it went
well. Same discipline as Phase 5 of the Architect/Executor pattern, applied to
configuration instead of code.

- **Read, never write.** This skill must be able to **read** a host's config even though
  it never writes it. The asymmetry is deliberate: reading is low-risk, needs no write
  permission, and degrades safely when a schema changes (the field isn't found, and the
  skill says so). Writing has none of those properties.
- **Behavioral fallback where reading isn't possible.** If a host exposes nothing
  inspectable, don't take "the file says opus" on faith — launch a trivial probe task and
  see who actually answers. Slower, but it's the only form that works against an arbitrary
  host.
- **Two checks a human wouldn't think to run:**
  - **Effort validity against the pinned model.** `xhigh` doesn't exist on Opus 4.6 or
    Sonnet 4.6; Claude Code silently falls back to the highest supported level at or below
    what was requested. An `xhigh` pin on an agent that resolves to 4.6 is an invisible
    regression — flag any effort/model combination that doesn't actually exist.
  - **Allowlist interaction.** A skill or subagent naming a model outside an
    organization's `availableModels` is ignored and silently runs on the session model
    instead. Only relevant under an organization-managed seat, not a personal plan — check
    for that context before treating this as a finding.
- **`CLAUDE_CODE_SUBAGENT_MODEL`.** If set in the environment, it overrides both the
  per-invocation `model` parameter and the subagent's frontmatter — every pin becomes
  inert. Check it explicitly, every run, before trusting a frontmatter read; it's a fact
  about the machine, not something to cache from a previous check.
- **Re-verification cadence: 24 hours, not "every session" and not "once, ever."**
  "Every session" re-pays a check that rarely has anything new to find; "once" is a
  guarantee that silently expires as plans change, allowlists tighten, or new models ship.
  Concretely: each `roles.toml` entry carries `last_verified`; treat an entry as stale (and
  re-run the read-only checks above for it) once `last_verified` is more than 24h old, or
  immediately on explicit request ("check whether the role setup still holds"). This is a
  starting point, not a law — revise the number if it proves too chatty or too stale in
  practice.
- **Re-verification re-runs Discovery, not just a status check.** If a fresh Discovery
  pass (step 1 of the Guided flow) surfaces a candidate that didn't factor into the
  original Ranking — a new model, a changed allowlist — surface that as a prompt to
  re-run the analysis for the affected role. Never silently rewrite `roles.toml`: a
  mapping changing underneath the operator is exactly the invisible drift this skill
  exists to prevent.
- **Attach it to something, or it won't run.** A validator nobody invokes implies a
  guarantee that doesn't exist, which is worse than no validator. The deterministic half
  of verification lives in `scripts/validate_roles.py` (see below) and is wired into
  `scripts/generate_skill_indices.py`, which already runs after every skill change in this
  repo — so the kit-internal checks (every skill declares a profile, no skill declares a
  model) run on a step that already exists rather than one someone has to remember.

## Companion script: `scripts/validate_roles.py`

Handles the deterministic half, deliberately **outside** the LLM-driven flow above — it's
a pure function of files on disk, and routing it through an LLM would cost tokens, be
non-reproducible, and risk a violation getting "interpreted" as acceptable one time in ten.

```bash
python3 scripts/validate_roles.py --plugin-dir <path/to/plugins/architect-side> --plugin-dir <path/to/plugins/executor-side> --plugin-dir <path/to/plugins/shared> [--roles-file ~/.config/ai-architect-executor/roles.toml]
```

Two independent groups of checks:

- **Kit-internal, always run** (no dependency on the operator's `roles.toml`, so this
  passes on a fresh checkout before anyone has run the guided flow):
  - every skill under each `--plugin-dir/skills/*/SKILL.md` has a matching entry in that
    plugin's `skill-requirements.json`, with a profile that is one of the four values above
    and a non-empty one-line reason;
  - no skill's `SKILL.md` frontmatter, and no `skill-requirements.json` entry, declares a
    `model` key.
- **Operator-config checks, only when `--roles-file` is given and exists:**
  - all four profiles are populated;
  - every populated role has a non-empty host and model (deeper host-side resolution —
    does this model ID actually exist, is it on the allowlist — is this skill's job at
    guided-flow / re-verification time, not the script's; the script only catches "this
    field was left empty", not "this field lies");
  - flags any `effort = "xhigh"` paired with a model known not to support it, against a
    small hardcoded table that degrades to "skip, unknown model" rather than failing
    closed when a model ID it doesn't recognize shows up;
  - if a role sets `basis`, its value must be one of the four evidence-basis slugs from
    "Ranking" above (`host-metadata`, `provider-tier-naming`, `model-self-knowledge`,
    `operator-stated`) — `basis` itself stays optional, this only catches a typo'd or
    invented one.

## `skill-requirements.json`

One per plugin, next to that plugin's `index.json`:

```json
{
  "conflict-resolver": { "profile": "deep-reasoning", "reason": "A merge decision disguised as conflict resolution; wrong calls compile but ship two overlapping mechanisms." },
  "interactive-role-setup": { "profile": "deep-reasoning", "reason": "A bad role mapping degrades every other skill silently, downstream, for as long as it goes unnoticed." }
}
```

This is the artifact `validate_roles.py` reads for the "every skill declares a profile"
check, and the answer to the open question about *where* the profile should live for skills
in this kit (see "Frontmatter vs. manifest" below).

## Frontmatter vs. manifest — resolved

The spec this skill was built from left one fact to verify empirically before deciding
where a skill's profile should be declared: does Kilo tolerate an unrecognized key in
`SKILL.md` frontmatter, or does it choke on it?

The literal test (install a throwaway skill with an `x-profile` key, see how Kilo's skill
loader reacts) couldn't be run end-to-end: the parser lives in the VS Code extension's
`opencode` package, not in the locally inspectable VSIX bundle, and this machine's `kilo`
CLI — which would exercise the same schema layer — currently fails before reaching any
subcommand, on an unrelated pre-existing config error (`Unrecognized key: marketplaces` in
`~/.config/kilo/kilo.jsonc`; flagged separately, not fixed here).

What *is* directly observable on this machine is that Kilo's config schema validation is
strict-by-default: an unrecognized top-level key in `kilo.jsonc` is a hard error, not a
silent ignore or a warning. Different schema than `SKILL.md` frontmatter, same team's
general design posture — and the spec's own fallback rule for an inconclusive test is to
default to the safer option anyway. Both point the same way: **profile lives in
`skill-requirements.json`, not as an extra frontmatter key.** Revisit if a future,
actually-run test on a working `kilo` CLI says otherwise.

## Non-goals

- Does not replace any tool's own configuration UI.
- Does not assume a specific model lineup — zero hardcoded references to "Opus", "Gemini",
  etc. in the logic; only ever in examples.
- Does not run unattended — see "It never runs unattended" above.
- Does not persist a per-project mapping — global only, for now (see "Config file" above).
