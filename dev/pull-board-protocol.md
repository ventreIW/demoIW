# Pull Board Protocol

The pull board (`work/epics/e{N}-{slug}/pull-board.md`) is the team's single source of truth for what is being worked on right now within an epic. Epics are logical containers — not branches. Each story gets its own branch (`story/s{N}.{M}/{slug}`) from `main`.

---

## States

| State | Meaning |
|---|---|
| `backlog` | Story is in scope for this epic but not started |
| `in-progress` | Story branch is active; someone is working it |
| `in-review` | Story work complete; awaiting retrospective + team review |
| `done` | Story merged to epic branch |
| `blocked` | Story cannot progress — reason must be stated |

---

## Pull board format

```markdown
# Pull Board — e{N}: {Epic Name}

Last updated: YYYY-MM-DD

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s{N}.1 | Story title | @name | in-progress | Started YYYY-MM-DD |
| s{N}.2 | Story title | — | backlog | |
```

---

## Rules

1. The pull board is updated immediately when a story changes state (GR-PROC-003).
2. At most **two stories in-progress simultaneously** per epic — this keeps reviews tight and reduces merge conflicts.
3. `blocked` state requires a reason and an owner responsible for unblocking.
4. The pull board is reviewed at the start of every working session (`/rai-session-start`).
5. A story cannot move to `done` without a completed retrospective file (`s{N}.{M}-retrospective.md`).

---

## Relationship to backlog

`governance/backlog.md` → epic `pull-board.md` → story files

- Items are pulled from the backlog into an epic pull board when `/rai-epic-start` is run.
- Items on the pull board are the committed scope for that epic.
- New scope discovered mid-epic goes to `dev/parking-lot.md` first, then backlog. Not directly into the active epic.
