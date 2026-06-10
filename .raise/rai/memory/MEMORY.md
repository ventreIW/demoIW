# Rai Memory — demoIW

> Permanent knowledge for this project. Loaded into system prompt.

---

## RaiSE Framework Process

### Work Lifecycle (Always Follow)

```
EPIC LEVEL:
  /rai-epic-start → /rai-epic-design → /rai-epic-plan → [stories] → /rai-epic-close

STORY LEVEL (per story):
  /rai-story-start → /rai-story-design* → /rai-story-plan → /rai-story-implement → /rai-story-review → /rai-story-close

* *design optional for S/XS stories

SESSION LEVEL:
  /rai-session-start → [work] → /rai-session-close
```

## Available Skills (17 total)

### Session Skills
- `/rai-session-start` — Load memory, analyze progress, propose focused work
- `/rai-session-close` — Capture learnings, update memory, log session

### Epic Skills
- `/rai-epic-start` — Initialize epic scope and directory structure
- `/rai-epic-design` — Design epic scope, stories, architecture
- `/rai-epic-plan` — Sequence stories with milestones and dependencies
- `/rai-epic-close` — Epic retrospective, metrics capture, tracking update

### Story Skills
- `/rai-story-start` — Create story branch and scope commit
- `/rai-story-design` — Create lean specification for complex stories
- `/rai-story-plan` — Decompose into atomic executable tasks
- `/rai-story-implement` — Execute tasks with TDD and validation gates
- `/rai-story-review` — Extract learnings, identify improvements
- `/rai-story-close` — Verify, merge, cleanup

### Discovery Skills
- `/rai-discover` — Full discovery pipeline — detect, extract, describe, document, build graph

### Meta Skills
- `/rai-skill-create` — Create new skills with framework integration

### Other Skills
- `/rai-research` — Epistemologically rigorous research
- `/rai-debug` — Root cause analysis using lean methods
- `/rai-framework-sync` — Sync framework files across locations

---

### Gate Requirements

| Gate | Required Before |
|------|-----------------|
| **Epic directory and scope initialized** | **Epic design** (/rai-epic-start) |
| **Story branch and scope commit** | **Story work** (/rai-story-start) |
| **Plan exists** | **Implementation** (/rai-story-plan) |
| **Retrospective complete** | **Story close** (/rai-story-review) |
| **Epic retrospective complete** | **Epic close** (/rai-epic-close) |
| Tests pass | Before any commit |
| Type checks pass | Before any commit |
| Linting passes | Before any commit |

---

## Critical Process Rules

1. **TDD Always** — RED-GREEN-REFACTOR, no exceptions
2. **Commit After Task** — Commit after each completed task, not just story end
3. **Full Skill Cycle** — Use skills even for small stories
4. **Ask Before Subagents** — Get permission before spawning subagents
5. **Delete Branches After Merge** — Clean up merged branches immediately
6. **HITL Default** — Pause after significant work for human review
7. **Direct Communication** — No praise-padding, say what needs saying
8. **Redirect When Dispersing** — Gently redirect tangents to parking lot
9. **Type Everything** — Type annotations on all code
10. **Pydantic Models** — Use Pydantic for all data structures
11. **Simple First** — Simple heuristics over complex solutions

---

## Branch Model

```
main (stable)
  └── main (development)
        └── story/s{N}.{M}/{name}
```

- Stories branch from and merge to main
- main merges to main at release
- Epics are logical containers (directory + tracker), not branches

---

## Key Patterns (from memory)

- **BASE-046:** Silent data drops are semantic bugs: when sync/upsert operations skip items, always report the skip count in the response.
- **BASE-047:** 3-tier config loading (built-in, project, user; last-wins) is the robust extensibility pattern for CLI tools — mirrors git config and XDG.
- **BASE-048:** Separation of concerns at integration boundaries: CLI owns domain concepts, adapter owns platform specifics.
- **BASE-049:** Dependency placement: protocols in core packages, implementations with external deps in consumer packages. Never add heavy dependencies to the leanest layer.
- **BASE-050:** Templates-as-contract: when tooling scaffolds files that parsers later consume, the template files ARE the contract. Store them as inspectable assets, not embedded strings.
- **BASE-051:** Hook extension pattern: typed event + subscriber + entry point + error isolation. Adding new cross-cutting behavior requires zero changes to existing code.
- **BASE-052:** Parallel research agents with distinct orthogonal questions produce higher-quality synthesis than sequential research — each goes deep on its axis, triangulation happens in synthesis.
- **BASE-053:** Separating parallel agent work by layer (e.g., code vs content, backend vs frontend) eliminates file collisions — the agent with freshest context on a file owns it.
- **BASE-054:** Explain-then-ask: present context and implications BEFORE requesting a decision. Questions without framing cause rejections and rework.
- **BASE-055:** U-shaped attention in LLMs: beginning and end get highest attention, middle is a dead zone (>30% accuracy drop). Position critical instructions at top and bottom of prompts.

---

*Last updated: 2026-06-10*
*Generated by `rai graph build`*
