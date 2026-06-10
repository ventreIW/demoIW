---
allowed-tools:
- Read
- Write
- Grep
- Glob
- Bash(rai:*)
description: Capture session outcomes and update memory. Use to close a working session.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.fase: end
  raise.frequency: per-session
  raise.gate: ''
  raise.inputs: '- session_id: string, required, previous_skill

    '
  raise.next: ''
  raise.outputs: '- session_record: file_path, file

    - patterns: list, cli

    '
  raise.prerequisites: ''
  raise.version: 4.2.0
  raise.visibility: public
  raise.work_cycle: session
name: rai-session-close
---

# Session Close

## Purpose

Close a session by reflecting on outcomes and feeding structured data to the CLI for atomic persistence.

## Mastery Levels (ShuHaRi)

- **Shu**: Detailed handoff with explanations of what was captured
- **Ha**: Standard handoff, explain only notable items
- **Ri**: Minimal handoff — next step and open items only

## Context

**When to use:** At the end of every working session.

**Quick close:** For short sessions, use CLI flags directly instead of a state file:
```bash
rai session close --summary "Quick fix session" --type maintenance --project .
```

## Steps

### Step 1: Craft Session Title

Generate a descriptive session title (max 80 chars) that captures what was accomplished — not planned, accomplished. Include the **epic/story name** (not just the number) so the title is self-explanatory without looking up Jira. Use the format: `SES-{ID}: {title}`.

**Good** (descriptive, includes context):
- `SES-321: E355 Branch Model Evolution cerrado + backlog review y priorización E354`
- `SES-318: E347 Backlog Automation — epic completo, 7 stories, merge a dev`
- `SES-316: Backlog sync + Semgrep MCP investigation`

**Bad** (too terse, requires lookup):
- `SES-321: E355 complete + backlog review`
- `SES-318: E347 done`

The title will be used in the `summary` field of the state file AND presented to the human for `/rename`.

### Step 2: Reflect & Produce State File

Use inference to reflect on the session and write a YAML state file.

**IMPORTANT:** Read `dev/parking-lot.md` first if it exists and you need to capture tangents — Claude Code requires reading a file before overwriting it.

State file structure (per-session, no collisions):

```yaml
# .raise/rai/sessions/{SES-ID}/output.yaml
session_id: "{SES-ID}"
summary: "{session_title}"  # The concise title from Step 1
type: feature  # feature | research | maintenance | infrastructure | ideation
outcomes:
  - "Concrete deliverable 1"
patterns:
  - description: "Pattern learned"
    context: "tag1,tag2"
    type: process
corrections:
  - what: "Behavioral observation"
    lesson: "Lesson learned"
coaching:                          # Only include fields that changed
  trust_level: "established"
  strengths: ["structured thinking"]
  growth_edge: "async patterns"
  autonomy: "high within defined scope"
  relationship:
    quality: "productive"
    trajectory: "stable"
current_work:
  release: V3.0
  epic: E15
  story: S15.7
  phase: implement
  branch: story/s15.7/session-protocol
pending:
  decisions: []
  blockers: []
  next_actions: ["Continue with Task 7"]
narrative: |
  ## Decisions
  - Key decisions and WHY
  ## Research
  - Conclusions with file paths
  ## Artifacts
  - Files created/modified
  ## Branch State
  - Branch and commits ahead of base
next_session_prompt: |
  Forward-looking guidance to future Rai. What to prioritize,
  what to watch for, what context will be critical.
```

**Capture tangents:** Check conversation for ideas → add to `dev/parking-lot.md`.

### Step 2.5: Detect Workarounds (Jidoka Gate)

**This step is a Jidoka enforcement gate — do not skip or combine with other steps.**

Before cleaning the working tree, scan the session narrative for workaround indicators that signal a deferred defect:

1. **Scan the narrative content** (from the `narrative:` field in the state file produced in Step 2) for:
   - CLI flags: `--frozen`, `--no-sync`, `--no-verify`, `--skip`, `--ignore`
   - Code markers: `# TODO`, `# HACK`, `# WORKAROUND`, `# FIXME`, `# XXX`
   - Patterns: `"not blocking"` + workaround description, `"skip"`, `"bypass"`, `"ignore for now"`, `"temp fix"`, `"temporary environment variable"`, `"workaround"`
   - Skip flags in pip/uv commands or environment overrides

2. **For each detected workaround:**
   - Ask the human: *"Workaround '{indicator}' detected in session narrative. Is there an existing bug ticket tracking this?"*
   - If **yes** (bug exists): note the bug key and continue — no action needed
   - If **no** (no bug): prompt: *"This workaround needs a bug ticket. Create one now? (y/n)"*
     - If **y**: open `rai backlog create` with a descriptive summary of the workaround
     - If **n**: log the workaround and add a note to the closing card: "⚠️ Untracked workaround: {description}"

3. **If no workarounds found:** proceed silently — no output needed.

**Detection heuristics:**
```yaml
indicators:
  cli_flags: ["--frozen", "--no-sync", "--no-verify", "--skip", "--ignore"]
  code_markers: ["# TODO", "# HACK", "# WORKAROUND", "# FIXME", "# XXX"]
  patterns: ["not blocking", "skip for now", "ignore for now", "temp fix", "workaround"]
environment_overrides: ["export VAR=", "set VAR=", "env VAR="]
```

False positives are acceptable — the step is a soft HITL gate. The human can always dismiss. False negatives (missed workarounds) are the real risk — err on the side of reporting.

<verification>
Session narrative scanned for workaround indicators.
All detected workarounds have an associated bug ticket OR are explicitly acknowledged by the human.
</verification>

### Step 2.7: Storage Integrity Check (non-blocking)

Quick check that the session's DB writes landed correctly. **Never blocks session close.**

```bash
python3 -c "
import sqlite3, pathlib
db = pathlib.Path('.raise/rai/raise.db')
if not db.exists(): exit(0)
conn = sqlite3.connect(str(db))
try:
    integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
    if integrity != 'ok':
        print(f'WARN: DB integrity check failed: {integrity}')
    else:
        print('DB integrity: ok')
finally:
    conn.close()
" 2>&1 || true
```

| Condition | Action |
|-----------|--------|
| Integrity ok | Continue silently |
| Integrity fails | Warn developer — do not block close |
| No DB / check fails | Continue silently |

### Step 3: Clean Working Tree

Before closing, ensure no staged, unstaged, or untracked files are left behind. Orphan files accumulate silently across sessions and pollute the working tree for future work.

1. Run `git status --short` AND `git ls-files --others --exclude-standard` (untracked files respecting .gitignore)
2. If working tree is fully clean (no output from either) → proceed to Step 4
3. **Staged changes (first column M/A/D)** — HIGH RISK. They persist across sessions and can silently revert remote work after a `git pull`. Present them prominently:
   ```
   WARNING: {N} staged changes will persist after this session closes.
   If not committed, they may conflict with or revert future pulls.

   Staged:
     D  path/to/deleted-file.py   ← DANGER: staged delete
     M  path/to/modified-file.py
   ```
   Options:
   - **Commit**: stage and commit with a descriptive message
   - **Unstage + Discard**: `git reset HEAD && git checkout .` (confirm first)
   - **Stash**: `git stash push -m "session-close-{SES-ID}-YYYY-MM-DD"`
   - **Leave**: explicitly acknowledge in the handoff AND in `next_session_prompt`
4. **Unstaged modifications (second column M/D)** — lower risk, present with options:
   - **Commit**: stage and commit
   - **Discard**: `git restore` (confirm first)
   - **Leave**: acknowledge in handoff
5. **Untracked files** — categorize and present a triage table:
   ```bash
   git ls-files --others --exclude-standard
   ```
   For each untracked file/directory, classify into one of:
   | Category | Examples | Default action |
   |----------|----------|----------------|
   | **Work artifacts** | `work/epics/*/stories/*`, `work/research/*` | Commit — these belong in the repo |
   | **Ephemeral/generated** | `*.db`, `*.backup.*`, `*-dead-letter.*`, `*.migrated` | Add to `.gitignore` |
   | **Misplaced** | transcripts in code repo, reports in wrong dir | Move to correct location, then commit or gitignore |
   | **Unknown** | anything unclear | Ask the developer |

   Present the triage as a summary table:
   ```
   {N} untracked files found:
     Commit:    {list}
     Gitignore: {list}
     Move:      {list} → {destination}
     Unknown:   {list}

   Proceed with this triage? (y/n/edit)
   ```
   Execute the chosen actions (commit, gitignore, move) before proceeding to Step 4.

6. Do NOT close the session with staged changes unless the human explicitly chooses "Leave" — and if they do, the `next_session_prompt` MUST warn the next session about them

### Step 4: Feed CLI

```bash
rai session close --state-file .raise/rai/sessions/{SES-ID}/output.yaml --session {SES-ID} --project .
```

This atomically: records session in index, appends patterns, updates coaching, writes session state, clears active session.

### Step 5: Commit CLI Artifacts

The CLI writes patterns and session state during Step 4. Commit these before presenting the closing card:

```bash
git add .raise/rai/memory/patterns.jsonl .raise/rai/session-state.yaml
# Only commit if there are staged changes (no empty commits)
git diff --cached --quiet || git commit -m "chore: persist session artifacts from {SES-ID}"
```

If `git add` fails (files don't exist or aren't modified), skip silently — not every session generates new patterns.

Present the closing card:

```
## Session Closed: SES-{ID} {session_title}

**Type:** {type}
**Outcomes:**
- {outcome 1}
- {outcome 2}
**Patterns:** {N new} | **Working tree:** {clean | N files uncommitted}

### Next Session
**Continue:** [next step]
**Open:** [unresolved questions, if any]
```

## Output

| File | Update | Writer |
|------|--------|--------|
| `.raise/rai/personal/sessions/index.jsonl` | Session record | CLI |
| `.raise/rai/sessions/{SES-ID}/output.yaml` | State file (per-session) | Skill (Write) |
| `.raise/rai/memory/patterns.jsonl` | New patterns | CLI |
| `~/.rai/developer.yaml` | Coaching + clear session | CLI |
| `.raise/rai/session-state.yaml` | Working state | CLI |
| `dev/parking-lot.md` | Tangents | Skill (Edit) |

## Quality Checklist

- [ ] Session ID matches the active session from session-start
- [ ] Summary reflects actual outcomes (not planned intent)
- [ ] Narrative enables next session to resume immediately
- [ ] Next session prompt is actionable and specific
- [ ] Workarounds detected and associated bugs created (or confirmed no workarounds exist)
- [ ] Tangents captured in parking lot (if any)
- [ ] Working tree clean — staged, unstaged, AND untracked files triaged
- [ ] Untracked files committed, gitignored, or moved — none left unaddressed
- [ ] CLI close command executed successfully

## References

- Complement: `/rai-session-start`
- Session state: `.raise/rai/session-state.yaml`
- Parking lot: `dev/parking-lot.md`
