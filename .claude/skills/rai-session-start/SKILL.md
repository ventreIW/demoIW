---
allowed-tools:
- Read
- Grep
- Glob
description: Load context and propose session focus. Use at the start of every working
  session.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.fase: start
  raise.frequency: per-session
  raise.gate: ''
  raise.inputs: '- project_path: string, required, argument

    - developer_profile: file_path, required, config

    '
  raise.next: ''
  raise.outputs: '- session_id: string, next_skill

    - context_bundle: string, cli

    '
  raise.prerequisites: ''
  raise.version: 6.0.0
  raise.visibility: public
  raise.work_cycle: session
name: rai-session-start
---

# Session Start

## Purpose

Load context bundle from CLI, interpret signals, and propose focused work for the session.

## Mastery Levels (ShuHaRi)

- **Shu**: Explain context, progress metrics, and concepts in presentation
- **Ha**: Explain only new or non-obvious signals
- **Ri**: Minimal output — context line, focus, signals, "Go."

## Context

**When to use:** At the start of every working session.

**When to skip:** Continuation of an active session (context already loaded).

**Inputs:** Developer profile (`~/.rai/developer.yaml`). If no profile exists, ask for the developer's name and pass `--name "Name"`.

## Steps

### Step 0: Working Tree Hygiene Check

Before anything else, check for orphan staged or unstaged changes that don't belong to the current session. These accumulate from worktree leaks, interrupted sessions, or forgotten stashes and can silently revert remote work.

```bash
git status --short
```

**Evaluate:**

| Condition | Action |
|-----------|--------|
| Clean (no output) | Continue to Step 1 |
| Only untracked files (`??`) | Continue to Step 1 — untracked files are harmless |
| Staged changes (`M`, `A`, `D` in first column) | **STOP** — present the list and ask the user to decide |
| Unstaged modifications (`M`, `D` in second column) | **WARN** — present the list, ask if intentional |

**When staged/unstaged changes are found, present:**

```
Working tree is not clean against HEAD. {N} staged changes, {M} unstaged modifications detected.

These may be residue from a prior session or worktree. If not addressed, they can silently
revert code that's already merged on the remote.

Staged deletes (highest risk):
  D  path/to/file.py
  ...

Options:
  1. Discard all local changes (git reset HEAD && git checkout .)
  2. Stash for later review (git stash push -m "session-start-orphans-YYYY-MM-DD")
  3. Keep and continue (I know what these are)
```

**Do NOT proceed to Step 1 until the user has chosen an option.** This gate is non-negotiable — orphan staged changes are the #1 cause of silent regressions on shared branches.

<verification>
Working tree is clean (or user explicitly chose to keep changes). No orphan staged changes remain.
</verification>

### Step 0.5: Storage Health Check (non-blocking)

Quick sanity check on SQLite storage. **Never blocks session start** — warn and continue.

```bash
rai db check 2>&1 || true
```

If `rai db check` is not available, run manually:

```bash
python3 -c "
import sqlite3, pathlib
db = pathlib.Path('.raise/rai/raise.db')
if not db.exists():
    print('WARN: No project database found')
elif db.stat().st_size == 0:
    print('WARN: Database is 0 bytes (phantom file)')
else:
    conn = sqlite3.connect(str(db))
    try:
        v = conn.execute('PRAGMA user_version').fetchone()[0]
        ic = conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()
        print(f'DB OK: schema v{v}, {len(ic)} tables')
    finally:
        conn.close()
" 2>&1 || true
```

| Condition | Action |
|-----------|--------|
| DB OK | Continue silently |
| Phantom file (0 bytes) | Warn: "Project DB is empty — run `rai db migrate` to initialize" |
| Schema version mismatch | Warn: "Schema v{N} found, expected v{M} — run `rai db migrate`" |
| No DB file | Continue silently — fresh project, DB created on first write |
| Check fails | Continue silently — storage health is advisory, not blocking |

<verification>
Storage health checked (or skipped silently on error). Warnings surfaced if found.
</verification>

### Step 1: Mission Selection

Select the mission for this session **before** loading the context bundle. The bundle includes mission-scoped memory, objectives, and patterns — these are only available if the mission is active when the bundle loads.

1. **Check if a mission is already active:**

```bash
rai mission list
```

| Condition | Action |
|-----------|--------|
| A mission is marked active | Skip to Step 2 — mission already bound |
| No missions exist (empty list) | Skip to Step 2 — nothing to select |
| Missions exist but none active | Continue to inference below |

2. **Infer likely mission from branch** (shortcut):

```bash
git branch --show-current
```

Extract the epic number from the branch name using the convention `story/s{epic}.{story}/{slug}` or `bugfix/s{epic}.{story}/{slug}`. Build the epic key as `E{number}` (e.g., branch `story/s1914.3/config-selector` → `E1914`).

Match the epic key against each mission's `linked_epics` field from the `rai mission list` output.

| Condition | Action |
|-----------|--------|
| Single mission matches the epic | Suggest it: "Mission **{name}** matches your branch (E{N}). Use for this session? (y/n)" |
| Multiple missions match | List the matches, ask user to pick one |
| No mission matches the branch | List all active missions, ask user to select or skip |
| Branch is a release/main branch (no epic extractable) | List all active missions, ask user to select or skip |

3. **Present selection to user:**

Always give the user these options:
- Accept the suggested mission
- Pick a different mission from the list
- Skip and work without a mission

Example presentation:

```
🎯 Mission detected from branch (E1914): **marketplace-v1**
   Objectives: 3 active | Sessions: 5 | Last used: 2h ago
   Use this mission? (y/n)
```

Or when no match:

```
No active mission. Available missions:
  1. marketplace-v1 (E1914) — 3 objectives, 5 sessions, 2h ago
  2. e2491-missions (E2491) — 2 objectives, 8 sessions, today
  3. Skip (no mission)

Select mission (1-N) or Enter to skip:
```

4. **Activate selected mission:**

```bash
rai mission switch {selected_mission_id}
```

This activates the mission AND regenerates MEMORY.md with mission-scoped memory. If the user skips, continue without a mission.

<verification>
Mission selected and activated (or explicitly skipped). MEMORY.md regenerated for mission scope.
</verification>

### Step 2: Load Orientation Bundle

```bash
rai session start --project . --context
```

Loads developer profile, session state, and orientation bundle. If graph unavailable: run `rai graph build` first.

The bundle now includes mission-scoped context (memories, objectives, last-session narrative) because the mission was activated in Step 1.

**IMPORTANT:** This is the ONLY `rai session start` CLI command in this skill. The context bundle output is complete — do NOT invent additional flags (e.g. `--section`), sub-commands (e.g. `rai context load`), or follow-up CLI calls to "fetch more". If the bundle mentions available context sections, that information is for display only. All interpretation happens in Step 3 using inference, not additional tool calls.

### Step 3: Interpret & Present

1. **Check signals** (priority order):
   - Next session prompt → guidance from your past self, highest-priority continuity
   - Release/deadline pressure → flag urgency with days remaining
   - Session narrative → review decisions, research, artifacts for continuity
   - Pending decisions or blockers → address first
   - Communication preferences → adapt tone

2. **Check MCP health** (non-blocking, never alarming):
   - Run `rai mcp list` to detect registered servers
   - If no servers registered: skip silently (no output)
   - If servers found: run `rai mcp health <name>` for each
   - Collect status: healthy count, unhealthy count, total
   - **If health check fails** (missing module, connection error, etc.): report as "not connected" — never show tracebacks or error details to the user. MCP servers are optional integrations, not critical infrastructure

3. **Propose session focus** from: pending items > current story/phase > deadlines

### Step 4: Bind Session to Jira Key (if current story has one)

If the orientation bundle identifies a current story with a Jira key, bind it to the per-session context file so CC hooks + MCP tool emissions inherit `RAISE_SESSION_JIRA_KEY` for this session (the bundle is the source of truth — resolve once, persist, stop):

```bash
rai session bind RAISE_SESSION_JIRA_KEY "{jira_key}"
```

The CLI uses line-replace semantics — it preserves other keys (e.g. `RAISE_SESSION_MISSION_ID`) and creates the session directory if needed. Skip silently if there's no bound Jira key — `jira_key=None` behavior is preserved. Namespacing by `$RAISE_CC_SESSION_ID` (RAISE-1982) prevents collisions between concurrent CC sessions in the same worktree.

4. **Present** (adapt verbosity to developer level):

```
## Session: YYYY-MM-DD

**Context:** [Release →] [Epic] → [Story], [phase]
**Mission:** {mission_name} ({epic_link}) — {N} objectives, {M} sessions
**Focus:** [goal]
**MCP:** [{total} servers, all healthy] or [{total} servers, {N} not connected — run /rai-mcp-status]
**Signals:** [any, or "None"]
```

If no mission is active, show:
```
**Mission:** None — run `rai mission new` or `rai mission switch` to bind
```

Omit the **MCP:** line entirely if no servers are registered.

## Output

| Item | Destination |
|------|-------------|
| Mission activated | Via `rai mission switch` (or skipped) |
| Session initialized | CLI session state updated |
| Focus proposed | Presented to developer |
| Next | Begin work on proposed focus |

## Quality Checklist

- [ ] Working tree hygiene verified (no orphan staged changes)
- [ ] Mission selected before bundle load (or explicitly skipped)
- [ ] Orientation bundle loaded successfully (with mission context if active)
- [ ] Signals interpreted in priority order
- [ ] Session focus proposed from pending work
- [ ] Verbosity adapted to developer ShuHaRi level
- [ ] MCP health checked when servers registered (silent skip if none)

## References

- Profile: `~/.rai/developer.yaml`
- Session state: `.raise/rai/session-state.yaml`
- Missions: `rai mission list`, `rai mission switch`
- MCP: `rai mcp list`, `rai mcp health`, `/rai-mcp-status`
- Complement: `/rai-session-close`
