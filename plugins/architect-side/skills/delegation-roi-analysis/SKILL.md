---
name: delegation-roi-analysis
description: "Evaluate delegation efficiency - ROI analysis (delegation cost vs. hypothetical inline-generation cost), defect-pattern review from logged issues, and feedback-loop proposals for better task specifications. Use when asked whether delegating to an Executor is paying off. Methodology only - concrete telemetry-tool calls live in the specific binding's own repo (e.g. kilo-mcp's mcp-metrics-analyst)."
---
<!-- GENERATED FROM SKILL.template.md — DO NOT EDIT BY HAND. Run generate_binding.py to regenerate. -->

# delegation-roi-analysis

This skill guides the Architect in evaluating and reporting delegation
efficiency and defect rates, using whatever telemetry the specific binding
collects. Protocol-agnostic: the questions below apply regardless of which
concrete tool call surfaces the numbers - see
[`kilo-mcp`](https://github.com/primax79/kilo-mcp)'s `mcp-metrics-analyst`
skill for the fully concrete version (specific tool names, JSONL schema)
this was distilled from.

## Logic and Behavior

- **ROI Analysis:** compare the actual delegation cost against the
  hypothetical cost of generating the same work inline (without
  delegating). Detail savings and efficiency multipliers to the user. Note
  that the real delegation cost includes the Executor's own execution
  cost when the operator pays for its tokens/compute - a "free" Executor
  changes the comparison to Architect-only cost (spec + review).
- **Defect Tracking:** review logged defects found during verification.
  Group them by severity and category to identify patterns.
- **Cancelled/aborted runs:** a task stopped mid-flight before completion
  still consumed real resources (the Executor's subprocess ran before
  being killed) and typically has no usable outcome record since no Final
  Report was produced. A high rate of cancellations for a given kind of
  task is itself a signal worth surfacing - it usually means the spec
  needs tighter constraints or the task is a poor fit for delegation.
- **Feedback Loop:** if recurring patterns are found (e.g. missed edge
  cases, styling mismatches, frequent cancellations), propose adding
  specific guardrails to future task specifications, or creating targeted
  Executor-side skills to close the gap - see `task-spec-authoring` for how
  task-spec quality itself is the main lever on defect rate.
