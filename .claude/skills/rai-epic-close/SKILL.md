---
allowed-tools:
- Read
- Edit
- Grep
- Glob
- Bash(rai:*)
- Bash(git:*)
description: Close epic with retrospective, push, and merge request. Use after all
  stories done.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.aspects: introspection
  raise.fase: '9'
  raise.frequency: per-epic
  raise.gate: ''
  raise.inputs: '- scope: file_path, required, previous_skill

    - all_retrospectives: boolean, required, git

    - dev_branch: string, required, config

    '
  raise.introspection:
    affected_modules: []
    context_source: all epic artifacts
    max_jit_queries: 3
    max_tier1_queries: 2
    phase: epic.close
    tier1_queries:
    - retrospective patterns for {domain} epics
    - process improvement patterns from similar epics
  raise.next: ''
  raise.outputs: '- retrospective: file_path, file

    - tag: string, git

    '
  raise.prerequisites: all stories complete
  raise.version: 3.2.0
  raise.visibility: public
  raise.work_cycle: epic
name: rai-epic-close
---

# Epic Close

## Purpose

Complete an epic by conducting a retrospective, tagging the milestone, and updating tracking. No branch merge needed — stories already merged to the development branch during story-close.

## Mastery Levels (ShuHaRi)

- **Shu**: Follow all steps, complete full retrospective template
- **Ha**: Adjust retrospective depth based on epic complexity
- **Ri**: Integrate with release workflows, automate metrics extraction

## Context

**When to use:** All stories complete and merged to `{dev_branch}`. Ready to close the epic lifecycle.

**When to skip:** Epic abandoned (document why, update backlog as "Abandoned").

**Inputs:** Epic scope document, all story retrospectives, passing test suite.

**Branch config:** Read `branches.development` from `.raise/manifest.yaml` for `{dev_branch}`. Default: `main`.

## Steps

### PRIME (mandatory — do not skip)

Before starting Step 1, you MUST execute the PRIME protocol:

1. **Chain read**: Read ALL learning records from this epic's skills (epic-design, epic-plan, and all story records). This provides the aggregate view for the retrospective.
2. **Graph query**: Execute tier1 queries from this skill's metadata using the `raise_graph_query` MCP tool. If MCP tools are not available, fall back to `rai graph query`. If graph is unavailable, note and continue.
3. **Present**: Surface retrieved patterns as context. 0 results is valid — not a failure.
4. **Emit start**: Signal lifecycle start for observability.
   ```bash
   rai signal emit-work epic "{epic_id}" --event start --phase close 2>/dev/null || true
   ```

### Step 1: Verify Stories Complete + Scope Re-read (mandatory)

**1a. Check all stories are done** in the epic scope document:

```bash
grep -E "^\s*-\s*\[ \]" "work/epics/e{N}-{name}/scope.md"
```

| Condition | Action |
|-----------|--------|
| All stories checked | Continue to 1b |
| Incomplete stories | Complete them first or explicitly descope |

**1b. Scope re-read (mandatory — do not skip)**: open `work/epics/e{N}-{name}/scope.md` and the original epic brief. Go through the **"In scope"** and **"Done when"** sections **item by item** and verify each commitment against observable state of the code. Do not trust "all stories checked ⇒ scope fulfilled" — it's not the same claim.

Pay special attention to commitments with elimination verbs (*"eliminate X"*, *"remove Y"*, *"replace Z with …"*, *"consolidate A and B"*). For each such commitment, answer one of three explicitly in the retrospective:

- **Fulfilled** — reference commit/file showing the removal
- **Descoped** — say why and link to a new epic/story that owns the remaining work
- **Not fulfilled** — stop. Do not close. Either finish the work or explicitly re-scope before closing

This exists because RCA s2092.1 showed E1323 ("eliminate subprocess layer") closed Done while the layer was actually **amplified** — the tools shipped, the tests passed, nobody re-read the scope (pattern `refactor-declared-done-without-sweep` at epic-scale).

> **JIT**: Before descoping decisions, query graph for completion patterns and prior descoping outcomes
> → `aspects/introspection.md § JIT Protocol`

<verification>
All stories marked complete in epic scope AND each "In scope" / "Done when" item re-verified against code. Elimination commitments resolved (fulfilled | descoped-with-link | not-fulfilled-stop).
</verification>

### Step 1.5: Reconcile Jira Child Story Status (RAISE-1847)

Query Jira for child stories that are NOT in Done status:

```bash
rai backlog search "parent = {EPIC_KEY} AND status != Done"
```

| Condition | Action |
|-----------|--------|
| No results (all Done) | Continue to Step 2 |
| Drifted stories found | Present the list and offer resolution (see below) |
| No Jira adapter configured | Warn: "Jira reconciliation skipped — no adapter" and continue |
| No epic Jira key | Warn: "No Jira key for epic — skipping reconciliation" and continue |
| Query fails (network, auth) | Warn: "Jira query failed �� manual check recommended" and continue |

**When drifted stories are found, present:**

```
Jira drift detected: {N} child stories are not in Done status.

  {KEY-1}  {status}  {summary}
  {KEY-2}  {status}  {summary}
  ...

Options:
  1. Batch-transition to Done: rai backlog batch-transition {KEY-1},{KEY-2} done
  2. Descope explicitly (document in retrospective why they're not Done)
  3. Abort epic close and fix the stories first
```

**Do NOT proceed to Step 2 until the user has chosen an option.** This gate prevents silent Jira drift that was found in E1690 audit (5 stories locally done but Backlog in Jira).

<verification>
Jira child stories reconciled: all in Done, or user explicitly descoped with documented reason. (Or no Jira adapter — warned and continued.)
</verification>

### Step 2: Write Retrospective

Do **not** run the full suite here — the full gate runs once in Step 4 via `/rai-mr-create`
before push. Trust the scoped gates that passed during story-close.

> **JIT**: Before writing retrospective, query graph for process improvement patterns from similar epics
> → `aspects/introspection.md § JIT Protocol`

Publish retrospective to local path and docs adapter. Use `templates/retrospective.md` as structure, fill from story retrospectives and git history:

```bash
rai docs write retrospective \
  --title "E{N}: {Epic Name} — Retrospective" \
  --stdin \
  --output-path work/epics/e{N}-{name}/retrospective.md << 'EOF'
[content following templates/retrospective.md structure]
EOF
```

<verification>
Tests green. Retrospective persisted locally and published via docs adapter. Metrics, patterns, and process insights included.
</verification>

### Step 3: Tag Epic Milestone

Tag the current `{dev_branch}` HEAD to mark epic completion:

```bash
git tag -a "epic/e{N}-complete" -m "Epic E{N}: {Epic Name} complete

Delivered: [key deliverables]
Stories: N stories

Co-Authored-By: Rai <rai@humansys.ai>"
```

Commit retrospective and any final artifacts:

```bash
git add -A
git commit -m "epic(e{N}): close with retrospective

Co-Authored-By: Rai <rai@humansys.ai>"
```

<verification>
Tag created. Retrospective committed.
</verification>

### Step 4: Push and Create Merge Request

Invoke `/rai-mr-create` — it runs the full gate suite, rebases onto target if needed,
pushes, and creates the MR. This is the single point where the full test suite runs.

```
/rai-mr-create
  source_branch: {dev_branch}
  target_branch: {main_branch}
  title: "epic(e{N}): {Epic Name}"
  description: |
    ## Epic E{N}: {Epic Name}

    ### Stories delivered
    - S{N}.1: {name}
    ...

    ### Key changes
    - {summary of deliverables}

    Co-Authored-By: Rai <rai@humansys.ai>
```

| Condition | Action |
|-----------|--------|
| Full gate passes | `/rai-mr-create` pushes and creates MR |
| Gate fails | Fix before push — do not skip |
| No release planned | Push dev only via `/rai-mr-create` without MR |

<verification>
Full gate passed via `/rai-mr-create`. Branch pushed. MR URL presented to developer.
</verification>

### Step 5: Update Backlog & Context

1. Mark epic complete — query done statuses and transition:
```bash
rai backlog statuses list --issue-type Epic
```
Infer close status (`category=done`, name suggests completion — not Cancelled/Rejected). If ambiguous, ask developer. Then:
```bash
rai backlog transition {JIRA_KEY} {done_slug}
```
If no Jira key, search first:
```bash
rai backlog search "summary ~ '{epic name}'"
```
Then transition the matching key.

| Condition | Action |
|-----------|--------|
| Jira key known | statuses list → infer → transition |
| No Jira key | search → resolve key → transition |
| Transition fails | Log warning and continue — non-blocking |

<verification>
Backlog reflects completion.
</verification>

## Output

| Item | Destination |
|------|-------------|
| Retrospective | `work/epics/e{N}-{name}/retrospective.md` |
| Tag | `epic/e{N}-complete` on `{dev_branch}` |
| Push | `{dev_branch}` pushed to origin |
| Merge request | GitLab MR: `{dev_branch}` → `{main_branch}` (if release) |
| Backlog update | Tracker via `rai backlog` CLI |

```bash
rai signal emit-work epic "{epic_id}" --event complete --phase close 2>/dev/null || true
```

**STOP HERE.** Return your summary to the orchestrator. Do NOT invoke any further skill.

## Quality Checklist

- [ ] All stories complete before closing (gate)
- [ ] Jira child stories reconciled — all Done, or explicitly descoped (RAISE-1847)
- [ ] Tests pass before closing
- [ ] Retrospective captures metrics, patterns, and process insights
- [ ] Epic milestone tagged on `{dev_branch}`
- [ ] Dev pushed to origin with all epic commits
- [ ] Merge request created if targeting main (epic-level MR, not per story)
- [ ] Backlog updated via `rai backlog transition` CLI
- [ ] No epic branch to clean up — epics are logical containers
- [ ] NEVER close without retrospective — learnings compound across epics
- [ ] NEVER create per-story MRs — one MR per epic at close time

## References

- Retrospective template: `templates/retrospective.md`
- Previous: All `/rai-story-close` completions
- Backlog: `rai backlog` CLI
- Next: `/rai-epic-design` for next epic
