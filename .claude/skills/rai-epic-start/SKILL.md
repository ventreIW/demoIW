---
allowed-tools:
- Read
- Edit
- Grep
- Glob
- Bash(rai:*)
- Bash(git:*)
description: Initialize epic directory, brief, and tracker entry. Use to begin a new
  epic.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.fase: '2'
  raise.frequency: per-epic
  raise.gate: ''
  raise.inputs: '- epic_id: string, required, argument

    - epic_slug: string, required, argument

    - dev_branch: string, required, config

    '
  raise.next: epic-design
  raise.outputs: '- brief: file_path, next_skill

    - scope: file_path, next_skill

    '
  raise.prerequisites: ''
  raise.version: 3.0.0
  raise.visibility: public
  raise.work_cycle: epic
name: rai-epic-start
---

# Epic Start

## Purpose

Initialize an epic with scope artifacts and a tracker entry. Epics are logical containers (directory + tracker), not branches. Story branches are created directly from the development branch.

## Mastery Levels (ShuHaRi)

- **Shu**: Follow all steps, verify each before proceeding
- **Ha**: Streamline scope for well-understood epics
- **Ri**: Integrate with release workflows and automated setup

## Context

**When to use:** Starting a new body of work (3-10 stories), beginning a planned epic from the backlog.

**When to skip:** Small fixes or single stories (no epic needed). Continuation of existing epic.

**Inputs:** Epic number (E{N}), epic name/slug, high-level objective.

**Branch config:** Read `branches.development` from `.raise/manifest.yaml` for `{dev_branch}`. Default: `main`.

## Steps

### Step 0: Instrument

```bash
rai signal emit-work epic "{epic_id}" --event start --phase init 2>/dev/null || true
```

### Step 1: Verify Development Branch

Ensure on `{dev_branch}` (for creating scope artifacts):

```bash
git branch --show-current
```

| Condition | Action |
|-----------|--------|
| On `{dev_branch}` | Continue |
| On other branch | `git checkout {dev_branch} && git pull` |

<verification>
On `{dev_branch}`, up to date with remote.
</verification>

### Step 2: Verify No Directory Collision

Before creating the epic directory, check that no existing directory would collide:

```bash
ls work/epics/ | grep -i "^e{N}-"
```

| Condition | Action |
|-----------|--------|
| No match | Continue — safe to create |
| Match found | **STOP** — directory `e{N}-*` already exists. Ask the developer to choose a different epic number |

This prevents ID collisions in the knowledge graph (RAISE-1199, RAISE-1204).

<verification>
No existing directory matches `e{N}-*` pattern.
</verification>

### Step 3: Define Scope & Commit

Create TWO artifacts via CLI:

1. `work/epics/e{N}-{name}/brief.md` — hypothesis, success metrics, appetite, rabbit holes:

```bash
rai docs write epic-brief \
  --title "E{N}: {epic-name} brief" \
  --stdin \
  --output-path work/epics/e{N}-{name}/brief.md << 'EOF'
[brief content following templates/brief.md]
EOF
```

2. `work/epics/e{N}-{name}/scope.md` — objective, in/out scope, planned stories, done criteria:

```bash
rai docs write epic-scope \
  --title "E{N}: {epic-name} scope" \
  --stdin \
  --output-path work/epics/e{N}-{name}/scope.md << 'EOF'
[scope content: objective, in/out scope, planned stories, done criteria]
EOF
```

Commit:

```bash
git add -A
git commit -m "epic(e{N}): initialize {epic-name}

Objective: {1-line}

In scope:
- {item 1}
- {item 2}

Co-Authored-By: Rai <rai@humansys.ai>"
```

Register epic in the backlog tracker:

**If Jira issue exists** — query available statuses and transition to start:
```bash
rai backlog statuses list --issue-type Epic
```
Infer start status (`category=indeterminate`, name suggests active work). If ambiguous, ask developer. Then:
```bash
rai backlog transition {JIRA_KEY} {start_slug}
```

**If new epic (no Jira key)** — verify credentials, read project key from backlog.yaml and create:

> **Credentials check (mandatory before creating):** Verify `JIRA_API_TOKEN` or `JIRA_API_TOKEN_HUMANSYS` is set in the environment. If not, source the project `.env` (`set -a && source .env && set +a`) or stop and ask the developer. **Never run `rai backlog create` without credentials** — it creates a local-only entry that silently syncs as a duplicate on the next credentialed invocation.

```bash
BACKLOG_PROJECT=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('.raise/backlog.yaml'))
orgs = cfg.get('jira', {}).get('organizations', {}).values()
projs = next(iter(orgs), {}).get('projects', [])
print(projs[0] if projs else '')
" 2>/dev/null)
rai backlog create "{title}" \
  -p "${BACKLOG_PROJECT}" \
  -t Epic \
  -l epic \
  -d "{objective — 1-line from the brief}"
```

| Condition | Action |
|-----------|--------|
| Jira key exists | statuses list → infer → transition |
| No key, project found | create with BACKLOG_PROJECT |
| Transition/create fails | Log warning and continue — non-blocking |

<verification>
Scope commit on `{dev_branch}`. Epic visible in backlog.
</verification>

<if-blocked>
Adapter not configured → log warning and continue. Backlog sync is best-effort.
</if-blocked>

### Step 3b: Create Epic Worktree Branch (when using a dedicated worktree)

If this epic is being developed in a dedicated git worktree, create the per-epic intermediate branch now:

```bash
git checkout -b worktree-{epic-slug} {dev_branch}
```

Stories will merge to this branch (not to `{dev_branch}` directly). Only `rai-epic-close` merges `worktree-{epic-slug}` → `{dev_branch}` via MR.

| Condition | Action |
|-----------|--------|
| Epic uses a dedicated git worktree | Create `worktree-{epic-slug}` from `{dev_branch}` — mandatory |
| Standalone epic on the main worktree | Skip — no intermediate branch needed |

<verification>
Worktree branch `worktree-{epic-slug}` created (or skip documented for standalone epic).
</verification>

### Step 4: Present Next Steps

Show the developer:
- Commit hash and epic directory path
- Quick scope summary (objective + story count)
- **Next:** `/rai-epic-design` to formalize scope and stories

## Output

| Item | Destination |
|------|-------------|
| Epic Brief | `work/epics/e{N}-{name}/brief.md` |
| Scope | `work/epics/e{N}-{name}/scope.md` |
| Scope commit | On `{dev_branch}` |
| Backlog entry | Tracker via `rai backlog` CLI |
| Next | `/rai-epic-design` |

```bash
rai signal emit-work epic "{epic_id}" --event complete --phase init 2>/dev/null || true
```

**STOP HERE.** Return your summary to the orchestrator. Do NOT invoke any further skill.

## Quality Checklist

- [ ] Epic Brief created from `templates/brief.md`
- [ ] Scope commit includes objective and boundaries
- [ ] Epic registered in tracker via `rai backlog` CLI
- [ ] Epic worktree branch `worktree-{epic-slug}` created when using a dedicated worktree
- [ ] NEVER skip worktree branch — stories must not merge directly to `{dev_branch}` in a dedicated worktree

## References

- Next: `/rai-epic-design`
- Stories: `/rai-story-start` (branches from `{dev_branch}`)
- Close: `/rai-epic-close`
- Branch model: `AGENTS.md` § Branch Model
