---
allowed-tools:
- Read
- Edit
- Grep
- Glob
- Bash(rai:*)
- Bash(git:*)
description: Create story branch and scope commit. Use to begin story work.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.fase: '3'
  raise.frequency: per-story
  raise.gate: ''
  raise.inputs: '- story_id: string, required, argument

    - dev_branch: string, required, config

    '
  raise.next: story-design
  raise.outputs: '- story_branch: string, next_skill

    - story_md: file_path, next_skill

    - scope_md: file_path, next_skill

    '
  raise.prerequisites: ''
  raise.version: 3.0.0
  raise.visibility: public
  raise.work_cycle: story
name: rai-story-start
raise.mastery:
  ha: Skip epic verification for standalone stories or experiments
  ri: Custom initialization patterns for specific workflows
  shu: Follow all steps, verify epic context, create branch with scope commit
---

# Story Start

## Purpose

Initialize a story with a dedicated branch from the development branch and a scope commit that documents boundaries and done criteria.

## Mastery Levels (ShuHaRi)

See `raise.mastery` in frontmatter.

## Context

**When to use:** Starting a new story from the backlog or epic scope.

**When to skip:** Quick bug fixes (direct branch). Continuation of already-started story.

**Inputs:** Story ID (S{N}.{M}), epic scope document (if part of an epic), clear understanding of story scope.

**Branch config:** Read `branches.development` from `.raise/manifest.yaml` for `{dev_branch}`. Default: `main`.

## Steps

### Step 0: Instrument

```bash
rai signal emit-work story "{story_id}" --event start --phase init 2>/dev/null || true
```

### Step 1: Verify Epic Context (if applicable)

If this story belongs to an epic, verify the epic directory and scope exist:

```bash
ls work/epics/e{N}-{name}/scope.md
```

| Condition | Action |
|-----------|--------|
| Epic scope exists | Continue — verify story is listed in scope |
| Epic scope missing | Run `/rai-epic-start` first |
| Standalone story | No epic verification needed |

<verification>
Epic context verified (or documented as standalone).
</verification>

### Step 2: Create Story Branch from Dev

Always branch from `{dev_branch}`:

```bash
git checkout {dev_branch} && git pull origin {dev_branch}
git checkout -b story/s{N}.{M}/{story-slug}
```

| Condition | Action |
|-----------|--------|
| M/L story | Create dedicated `story/` branch |
| S/XS story | Create branch anyway — all stories branch from `{dev_branch}` |
| Standalone | Same — `story/s{N}.{M}/{slug}` from `{dev_branch}` |

<verification>
On story branch created from `{dev_branch}`.
</verification>

### Step 3: Define Scope & Commit

Create TWO artifacts:

1. `work/epics/e{N}-{name}/stories/s{N}.{M}-story.md` — publish via docs adapter using `templates/story.md` as structure:

```bash
rai docs write story \
  --title "S{N}.{M}: {story-name}" \
  --stdin \
  --output-path work/epics/e{N}-{name}/stories/s{N}.{M}-story.md << 'EOF'
[user story content following templates/story.md: Connextra format, Gherkin AC, SbE examples]
EOF
```

2. `work/epics/e{N}-{name}/stories/s{N}.{M}-scope.md` — in scope/out of scope, done criteria (observable outcomes):

```bash
rai docs write story-scope \
  --title "S{N}.{M}: {story-name} scope" \
  --stdin \
  --output-path work/epics/e{N}-{name}/stories/s{N}.{M}-scope.md << 'EOF'
## In Scope
{items}

## Out of Scope
{items}

## Done when
{observable outcomes}
EOF
```

Commit:

```bash
git branch --show-current | grep -qx "story/s{N}.{M}/{story-slug}" && \
git add work/epics/e{N}-{name}/stories/s{N}.{M}-story.md \
        work/epics/e{N}-{name}/stories/s{N}.{M}-scope.md && \
git commit -m "feat(s{N}.{M}): initialize story scope

In scope:
- {item 1}
- {item 2}

Done when:
- {criteria 1}
- {criteria 2}

Co-Authored-By: Rai <rai@humansys.ai>"
```

When committing from a non-CWD worktree, prefix the same chain with `cd /path/to/worktree &&` so the branch assertion and `git add` execute in one shell command.

<verification>
Scope commit on story branch with boundaries documented.
</verification>

### Step 3b: Update Backlog Status

Query available statuses for this issue type:
```bash
rai backlog statuses list --issue-type Story
```

Infer start status from output:
- Look for `category=indeterminate` states whose name suggests active work
  (Implement, In Progress, Started, Active, WIP, Doing…)
- Single clear candidate → use it silently
- Multiple candidates or ambiguous name → ask developer:
  *"Which status means 'work started'? Options: [list]"*

Transition (non-blocking):
```bash
rai backlog transition {story_key} {start_slug}
```
`{start_slug}` = status name lowercased, spaces→hyphens
("Implement" → `implement`, "In Progress" → `in-progress`)

| Condition | Action |
|-----------|--------|
| Clear candidate found | Transition silently |
| Ambiguous | Ask developer before transitioning |
| No ticket | Skip |
| Transition fails | Log warning and continue |

<if-blocked>
Adapter not configured or transition fails → log and continue. Backlog sync is best-effort; it must never block story work.
</if-blocked>

### Step 3c: Bind Session to Jira Key

When the story has a Jira key, bind it to the per-session context file so CC hooks + MCP tool emissions inherit `RAISE_SESSION_JIRA_KEY` on the next session restart (or fall back to it when the MCP subprocess env misses):

```bash
rai session bind RAISE_SESSION_JIRA_KEY "{story_key}"
```

The CLI uses line-replace semantics — it preserves other keys (e.g. `RAISE_SESSION_MISSION_ID`) already in the file. Namespacing by `$RAISE_CC_SESSION_ID` (RAISE-1982) prevents collisions between concurrent CC sessions in the same worktree.

| Condition | Action |
|-----------|--------|
| Story has Jira key | Bind the key + emit `session_bind` event |
| No Jira key (standalone/local story) | Skip — `jira_key=None` preserved |

After binding, emit a `session_bind` event so the server associates this session with the Jira key (S2017.5 — late-bind):

```bash
python3 .claude/hooks/_emit_hansei.py \
    --event-type session_bind \
    --title "Bound {story_key}" \
    --summary "Late-bind jira_key to session" \
    --jira-key "{story_key}" \
    --session-id "$RAISE_CC_SESSION_ID" \
    --tags "kind:lifecycle"
```

This is fire-and-forget — if emission fails (no server configured), the context.env file still provides local fallback.

<verification>
`.raise/rai/sessions/$RAISE_CC_SESSION_ID/context.env` contains `RAISE_SESSION_JIRA_KEY={story_key}` (other keys preserved).
`session_bind` event emitted (or skipped silently if no server).
</verification>

### Step 4: Present Next Steps

Show the developer:
- Branch name and commit hash
- Quick scope summary
- **Next:** `/rai-story-design` — design is not optional (PAT-186)

## Output

| Item | Destination |
|------|-------------|
| Story branch | `story/s{N}.{M}/{slug}` from `{dev_branch}` |
| User Story | `stories/s{N}.{M}-story.md` (local) + docs adapter (type: story) |
| Scope commit | On story branch |
| Backlog update | via `rai backlog transition` (best-effort) |
| Signal | WorkLifecycle event emitted (start on entry, complete here) |

```bash
rai signal emit-work story "{story_id}" --event complete --phase init 2>/dev/null || true
```

**STOP HERE.** Return your summary to the orchestrator. Do NOT invoke any further skill.

## Quality Checklist

- [ ] NEVER create story branch from anything other than `{dev_branch}`

## References

- Next: `/rai-story-design` (always — PAT-186)
- Complement: `/rai-story-close`
- Epic scope: `work/epics/e{N}-{name}/scope.md`
- Branch model: `AGENTS.md` § Branch Model
