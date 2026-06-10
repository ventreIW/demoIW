---
allowed-tools:
- Read
- Grep
- Glob
- Bash(rai:*)
description: Extract learnings and persist patterns from completed story. Use after
  implementation.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.aspects: introspection
  raise.fase: '7'
  raise.frequency: per-story
  raise.gate: ''
  raise.inputs: '- tests_passing: boolean, required, cli

    '
  raise.introspection:
    affected_modules: []
    context_source: all story artifacts
    max_jit_queries: 3
    max_tier1_queries: 2
    phase: story.review
    tier1_queries:
    - evaluation patterns for {affected_modules}
    - process patterns from recent stories
  raise.next: story-close
  raise.outputs: '- retrospective_md: file_path, next_skill

    - patterns: list, cli

    '
  raise.prerequisites: story-implement
  raise.version: 2.5.0
  raise.visibility: public
  raise.work_cycle: story
name: rai-story-review
raise.mastery:
  ha: Adapt depth to story complexity, batch small story reviews
  ri: Custom review patterns, integrate with team retrospectives
  shu: Follow all steps, answer all checkpoint questions with specific examples
---

# Story Review

## Purpose

Reflect on the completed story to extract learnings, persist patterns, reinforce behavioral signals, and emit calibration telemetry.

## Mastery Levels (ShuHaRi)

See `raise.mastery` in frontmatter.

## Context

**When to use:** After implementation is complete and tests pass. Before `/rai-story-close`.

**Inputs:** Completed story, progress log, passing test suite.

## Steps

### PRIME (mandatory — do not skip)

Before starting Step 1, you MUST execute the PRIME protocol:

1. **Graph query**: Execute tier1 queries from this skill's metadata using the `raise_graph_query` MCP tool. If MCP unavailable, fall back to `rai graph query`. 0 results is valid.
2. **Emit start**:
   ```bash
   rai signal emit-work story "{story_id}" --event start --phase review 2>/dev/null || true
   ```

### Step 1: Verify Tests Pass

Trust the end-of-story scoped gate from `/rai-story-implement` Step 5 — do **not** re-run
the full suite here. Review requires that the scoped gates passed; the full suite runs once
at push time via `/rai-mr-create`.

```bash
# Confirm the implement-complete signal was emitted for the current HEAD
rai signal query story "{story_id}" --event complete --phase implement \
  --session-id "${RAISE_CC_SESSION_ID}" --latest --fields commit 2>/dev/null
```

| Condition | Action |
|-----------|--------|
| Signal found for current HEAD | ✓ Tests already verified — continue |
| Signal missing or stale commit | Run scoped package gate: `rai gate check gate-tests --scope packages/<pkg>/` |
| Scoped gate fails | Fix before reviewing — review requires green tests |

<verification>
Implement-complete signal confirmed for current HEAD (or scoped gate re-run and passing).
</verification>

### Step 2: Gather Data & Reflect

> **JIT**: Before reflecting on development process, query graph for evaluation patterns
> → `aspects/introspection.md § JIT Protocol`

Review the story development: actual vs estimated time, blockers, plan deviations.

**Heutagogical checkpoint** — answer with specific examples:
1. What did you learn?
2. What would you change about the process?
3. Are there improvements for the framework?
4. What are you more capable of now?

Identify concrete improvements to skills, guardrails, or templates. Apply small improvements immediately; create issues for complex ones.

<verification>
All four questions answered. Improvements identified (or celebrated that none needed).
</verification>

### Step 3: Aggregate Learning Records

Read learning records produced during this story's lifecycle:
- `.raise/rai/learnings/rai-story-design/{work_id}/record.yaml`
- `.raise/rai/learnings/rai-story-plan/{work_id}/record.yaml`
- `.raise/rai/learnings/rai-story-implement/{work_id}/record.yaml`

If any record is missing (silent node or execution gap), note it and continue — missing records are valid signal.

Produce aggregate summary with these metrics:

| Metric | Calculation | What it tells us |
|--------|-------------|-----------------|
| **Acceptance rate** | Patterns voted +1 / total patterns primed | Are PRIME queries returning useful context? |
| **Gap rate** | Total gaps / total JIT queries | Is the graph missing knowledge we need? |
| **Pattern utility** | Patterns +1 / (patterns +1 + patterns -1) | Are stored patterns helping or misleading? |

Include the aggregate in the retrospective (Step 5).

<verification>
Learning records read (or missing noted). Metrics calculated. Aggregate ready for retrospective.
</verification>

### Step 4: Persist Patterns & Reinforce

> **JIT**: Before persisting patterns, query graph for existing patterns to avoid duplicates
> → `aspects/introspection.md § JIT Protocol`

**Add new patterns** worth preserving across sessions using the `raise_pattern_add` MCP tool with content="Pattern description", context="context,keywords", pattern_type="process", from_story="S{N}.{M}".

If MCP tools are not available, fall back to:
```bash
rai pattern add "Pattern description" -c "context,keywords" -t process --from S{N}.{M}
```

Types: `process`, `technical`, `architecture`, `codebase`.

**Reinforce existing patterns** — evaluate behavioral patterns loaded at session start using the `raise_pattern_reinforce` MCP tool with pattern_id={pattern_id}, vote={1|0|-1}, from_story="S{N}.{M}".

If MCP tools are not available, fall back to:
```bash
rai pattern reinforce {pattern_id} --vote {1|0|-1} --from S{N}.{M}
```

| Vote | Meaning |
|:----:|---------|
| `1` | Implementation followed the pattern |
| `0` | Pattern not relevant to this story (does NOT count toward evaluations) |
| `-1` | Implementation contradicted the pattern |

Only evaluate patterns you consciously considered. `0` is correct for most patterns in any story.

<verification>
New patterns persisted. Behavioral patterns evaluated (or explicitly skipped).
</verification>

### Step 5: Document Retrospective

Publish retrospective to local path and docs adapter via:

```bash
rai docs write story \
  --title "S{N}.{M}: {story-name} — Retrospective" \
  --stdin \
  --output-path work/epics/e{N}-{name}/stories/s{N}.{M}-retrospective.md << 'EOF'
# Retrospective: S{N}.{M} — {story-name}

**Dates:** {start-date} → {end-date}
**Estimated:** {estimated} | **Actual:** {actual}

## Summary
{summary}

## What went well
{went-well}

## What to improve
{to-improve}

## Heutagogical Checkpoint
1. **What did I learn?** {answer}
2. **What would I change about the process?** {answer}
3. **Framework improvements?** {answer}
4. **More capable of now?** {answer}

## Improvements applied
{improvements}

## Patterns added / reinforced
{patterns}

## Learning chain summary
{records-found-or-missing, aggregate metrics, notable gaps, downstream enrichments}
EOF
```

<verification>
Retrospective persisted locally and published via docs adapter. Learning chain summary included.
</verification>

## Output

| Item | Destination |
|------|-------------|
| Retrospective | `work/epics/e{N}-{name}/stories/s{N}.{M}-retrospective.md` (local) + docs adapter (type: story) |
| Patterns | `.raise/rai/memory/patterns.jsonl` |
| Signal | WorkLifecycle event emitted (start on entry, complete here) |

Transition story to review status before signaling completion (non-blocking):
```bash
rai backlog statuses list --issue-type Story
```
Infer review status: `category=indeterminate` + name contains Review, Revision, Code Review.
Single candidate → transition silently. Multiple or ambiguous → ask developer. None → skip silently.
```bash
rai backlog transition {story_key} {review_slug}
```

```bash
rai signal emit-work story "{story_id}" --event complete --phase review 2>/dev/null || true
```

**STOP HERE.** Return your summary to the orchestrator. Do NOT invoke any further skill.

## Quality Checklist

- [ ] NEVER skip pattern reinforce — scoring system depends on it (RAISE-170)
- [ ] NEVER give vague checkpoint answers — be specific with concrete examples

## References

- Previous: `/rai-story-implement`
- Next: `/rai-story-close`
- Pattern scoring: RAISE-170 (temporal decay + Wilson scorer)
