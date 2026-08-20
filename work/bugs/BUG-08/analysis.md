# BUG-08: analysis

## Method: Requirement-to-schema trace

There is no failure to reproduce — the system behaves as built. The method is to take the
requirement's four mandated fields and trace each to a storage location, which either exists
or does not.

## The trace

| NFR-06 field | Produced at | Available? | Persisted? |
|---|---|---|---|
| timestamp (draft) | `generate_communication_draft.py:136` | yes | ✅ `created_at` |
| model used | `communication_draft_service.py:43` `self._model` | **yes — in scope at draft time** | ❌ discarded |
| prompt version | `communication_draft_service.py:47` `communications/v1_draft.txt` | **yes — the filename encodes it** | ❌ discarded |
| operator identifier | nowhere | **no — does not exist in this system** | ❌ |
| timestamp (send) | `cases.py:284` | yes (`datetime.now`) | ❌ not recorded |

## Root cause

**Two distinct causes, and conflating them is what makes this look bigger than it is.**

**Cause 1 — three fields are discarded, not missing.** Model, prompt version and send time are
all in scope at the moment the record is written. `generate_communication_draft.py:129`
constructs `Communication(...)` with seven fields and simply does not carry them across; the
draft service knows the model and template it used and has no reason to volunteer them,
because nothing asks. `send_communication` rebuilds the entity field-by-field to flip `status`,
which is the exact place a `sent_at` would be stamped, and stamps nothing. This half is
mechanical: widen the record and pass what is already in hand.

**Cause 2 — the operator identifier does not exist.** This product has no authentication. B-17
("Role-based access — operator vs. executive") is still in the backlog's *Under consideration*
section, explicitly undecided. There is no session, no user table, no principal on the request.

Cause 2 is why the whole requirement stalled rather than being half-implemented: one of the
four fields had no source, so none of the four were done. That is a recognisable failure shape
— *an all-or-nothing reading of a requirement whose parts have different costs.* Three of these
four fields were free.

## The honesty constraint on the operator field

The tempting fix is a literal like `operator_id = "operator"`. That would satisfy the schema
and **falsify the audit record**, which is worse than leaving it null: an audit trail whose
provenance is invented is not an audit trail. §2 of the vision ("stop on defects") and the
project's own standard — visible degradation over silent wrongness, established in s4.8's
`EnrichmentOutcome` and ADR-009's `scored_at` — both point the other way.

The correct shape is the one this codebase already uses for unavailable provenance: record
what is actually known, and make the placeholder self-describing. An `X-Operator-Id` header
when supplied, and an explicit configured default (`demo-operator`) that names itself as a
demo placeholder, is truthful. When B-17 lands, the header becomes the authenticated
principal and nothing else changes.

## Why it survived

s5.4 designed the communications schema and s5.5 built the send flow. Neither story's
acceptance criteria referenced NFR-06 — E5's scope lists "draft persistence + audit log" in
its in-scope table, and "audit" was satisfied by the *existence* of a persisted
`CommunicationORM` row rather than by the PRD's field list. The word matched; the requirement
did not.

Nothing checked. NFR-01 through NFR-05 each acquired a verifying test during E7
(`test_e2e_demo_flow`, `test_nfr02_performance`, the axe scan, the manifest, the key-parity
guard). NFR-06 acquired none, and was the only NFR never mentioned in this session until the
completion review enumerated the PRD.

## Fix approach

Widen `CommunicationORM` with `operator_id`, `model_used`, `prompt_version`, `sent_at`
(migration `0005`). Have the draft service report the model and template version it actually
used rather than having the use case guess. Stamp `sent_at` at the send seam. Take the
operator from an `X-Operator-Id` header with a self-describing configured default. Backfill
existing rows with `NULL` provenance rather than inventing values — a row drafted before this
change genuinely does not know which model wrote it, and should say so.
