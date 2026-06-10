---
allowed-tools:
- Read
- Grep
- Glob
- Bash(rai:*)
description: Decompose story into atomic tasks with TDD verification. Use after story
  design.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.aspects: introspection
  raise.fase: '5'
  raise.frequency: per-story
  raise.gate: gate-plan
  raise.inputs: '- design_md: file_path, optional, previous_skill

    - story_md: file_path, required, story-start

    '
  raise.introspection:
    affected_modules: []
    context_source: design doc
    max_jit_queries: 2
    max_tier1_queries: 3
    phase: story.plan
    tier1_queries:
    - decomposition patterns for {complexity} stories
    - TDD patterns for {affected_modules}
    - estimation calibration for {size} stories
  raise.next: story-implement
  raise.outputs: '- plan_md: file_path, next_skill

    '
  raise.prerequisites: project-backlog
  raise.version: 2.3.0
  raise.visibility: public
  raise.work_cycle: story
name: rai-story-plan
raise.mastery:
  ha: Adjust granularity based on complexity, parallelize when possible
  ri: Custom planning patterns for specific stacks
  shu: Decompose each story into atomic tasks with full verification criteria
---

# Story Plan

## Purpose

Decompose a story into atomic executable tasks with dependencies, verification criteria, and a deterministic execution order.

## Mastery Levels (ShuHaRi)

See `raise.mastery` in frontmatter.

## Context

**When to use:** After `/rai-story-design` has grounded integration decisions (or directly for simple stories).

**Prerequisite:** Design document at `work/epics/e{N}-{name}/stories/s{N}.{M}-design.md` (optional for simple stories).

**Inputs:** Story with acceptance criteria, design document (if exists).

## Steps

### PRIME (mandatory — do not skip)

> **Token marker** — Call `raise_session_topic(kind="plan", topic="prime")` before executing this step.

Before starting Step 1, you MUST execute the PRIME protocol:

1. **Graph query**: Execute tier1 queries from this skill's metadata using the `raise_graph_query` MCP tool. If MCP unavailable, fall back to `rai graph query`. 0 results is valid.
2. **Emit start**:
   ```bash
   rai signal emit-work story "{story_id}" --event start --phase plan 2>/dev/null || true
   ```

### Step 1: Verify Design

> **Token marker** — Call `raise_session_topic(kind="plan", topic="verify-design")` before executing this step.

```bash
ls work/epics/e*/stories/{story_id}-design.md 2>/dev/null || echo "INFO: No design"
```

> **JIT**: Before verifying design completeness, query graph for complexity assessment patterns
> → `aspects/introspection.md § JIT Protocol`

| Condition | Action |
|-----------|--------|
| Design exists | Load and reference |
| No design + simple story | Continue |
| No design + complex story | Run `/rai-story-design` first |

<verification>
Design loaded or simple story confirmed.
</verification>

### Step 2: Decompose into Tasks

> **Token marker** — Call `raise_session_topic(kind="plan", topic="decompose")` before executing this step.

Divide story into atomic, individually verifiable tasks. One commit per task.

| Story Size | Tasks | Rationale |
|------------|:-----:|-----------|
| XS (1-2 SP) | 1-2 | Single-pass implementation |
| S (3-5 SP) | 2-3 | Avoid over-decomposition |
| M (5-8 SP) | 3-5 | Balance granularity and overhead |
| L (8+ SP) | 5-8 | Consider splitting the story |

**Per task:**
- Description, files to create/modify
- TDD cycle: RED (failing test) → GREEN (minimal code) → REFACTOR
- AC reference: link to `story.md` Gherkin scenario (if exists)
- Verification: specify the `rai gate check` commands with explicit `--scope` (see Gate Policy below)
- Size (XS/S/M/L) and dependencies

**Always include as final task:** Manual integration test — validate end-to-end with running software.

**Gate Policy (mandatory in every plan):**

Include this section verbatim in the plan document — it keeps the test execution rules in context during `/rai-story-implement`:

| When | Command | Scope |
|------|---------|-------|
| Per task | `rai gate check gate-tests --scope <test_dir>/` | Only tests for the changed module (e.g. `packages/raise-cli/tests/storage/`) |
| Per task | `rai gate check gate-lint` | Full project (fast) |
| Per task | `rai gate check gate-format` | Full project (fast) |
| Per task | `rai gate check gate-types` | Full project |
| End of story | `rai gate check gate-tests --scope packages/<pkg>/` | Changed package only — NOT full suite |
| MR creation | `/rai-mr-create` | Full suite — the ONLY place where unscoped tests run |

**NEVER run test commands directly** (e.g. `uv run pytest`, `npm test`) — always use `rai gate check`. Direct invocation floods context with raw output and bypasses gate tracking.

Each task's Verification section MUST use `rai gate check gate-tests --scope <path>` with the concrete test path for that task. Generic or unscoped test commands are not acceptable.

<verification>
Each task is atomic and verifiable. Final integration test included.
</verification>

### Step 3: Order & Dependencies

> **Token marker** — Call `raise_session_topic(kind="plan", topic="order")` before executing this step.

> **JIT**: Before ordering dependencies, query graph for risk-first ordering patterns
> → `aspects/introspection.md § JIT Protocol`

- Map dependencies (sequential vs parallel)
- Apply risk-first ordering (riskiest tasks early)
- Maximize parallelism where no mutual dependencies exist
- Verify no circular dependencies

<verification>
Execution order defined. Dependency graph is acyclic.
</verification>

### Step 4: Document Plan

> **Token marker** — Call `raise_session_topic(kind="plan", topic="document")` before executing this step.

Publish `work/epics/e{N}-{name}/stories/s{N}.{M}-plan.md` via CLI:

```bash
rai docs write story-plan \
  --title "S{N}.{M}: {story-name} plan" \
  --stdin \
  --output-path work/epics/e{N}-{name}/stories/s{N}.{M}-plan.md << 'EOF'
[plan content below]
EOF
```

Content to include:
- Overview (story ID, size, date)
- Ordered task list with descriptions, files, verification, sizes, dependencies
- Execution order with rationale
- Risks and mitigations
- Duration tracking table (filled during implementation)

<verification>
Plan document complete and reviewable in <5 minutes.
</verification>

## Output

| Item | Destination |
|------|-------------|
| Implementation plan | `work/epics/e{N}-{name}/stories/s{N}.{M}-plan.md` |
| Signal | WorkLifecycle event emitted (start on entry, complete here) |

Transition story to implement status before signaling completion (non-blocking):
```bash
rai backlog statuses list --issue-type Story
```
Infer implement status: `category=indeterminate` + name contains Implement, Progress, Development.
Single candidate → transition silently. Multiple or ambiguous → ask developer. None → skip silently.
```bash
rai backlog transition {story_key} {implement_slug}
```

```bash
rai signal emit-work story "{story_id}" --event complete --phase plan 2>/dev/null || true
```

**STOP HERE.** Return your summary to the orchestrator. Do NOT invoke any further skill.

## Quality Checklist

- [ ] NEVER over-decompose simple stories
- [ ] NEVER skip TDD guidance — tests define behavior
- [ ] NEVER write `uv run pytest` / `npm test` in verification — always `rai gate check gate-tests --scope`
- [ ] Gate Policy section included in plan document with concrete --scope paths per task

## References

- Gate: `gates/gate-plan.md`
- Previous: `/rai-story-design`
- Next: `/rai-story-implement`
