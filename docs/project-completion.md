# demoIW — project completion record

**Tagged:** `v1.0.0`, 2026-08-20 · **Period:** 2026-05-04 → 2026-08-20
**Company:** InterWare México S.A. de C.V. · **Framework:** RaiSE

Aplicación Web para la gestión integral de ventas organizacionales — a demonstrative
accounts-receivable and collections product.

---

## The vision's five measurable outcomes, verified

`governance/vision.md` defines completion. Each outcome is checked against observable state,
not against the epic tracker.

### 1. Demo produces conviction — the full flow in under 10 minutes ✅

`backend/tests/test_e2e_demo_flow.py` drives all ten presenter steps in order — generate,
activate, score, prioritised queue, category filter, case detail, contact result,
communication draft, executive KPIs, natural-language query — and completes in **1.41 s**
against NFR-01's 600 s budget. It is proven able to fail: two deliberate breakages were
injected and each was caught with a precise diagnostic.

Both LLM paths are covered — the degraded path (the model is unavailable) and the success
path (chart, narrative and citation), the latter also guarding the reasoning-trace leak s6.3
found in live verification.

### 2. Coverage of the student competency profile ⚠️ *(evidence complete, grouping unconfirmed)*

`docs/tsu-dsm-competency-coverage.md` maps every competency area of the published *perfil de
egreso* to concrete artifacts, with sources. **The one caveat in this document:** the
published profile is prose, not a numbered list, so the grouping into exactly six headings is
a reading rather than a citation. Renata or Gustavo should confirm against the program's own
framework. The evidence rows are factual and survive any regrouping.

Two honest gaps the grounding exposed: **security is the thinnest area** — this product has
no authentication by design (B-17 undecided), which is why NFR-06's operator identifier is a
self-described placeholder — and **IoT is not exercised at all**.

### 3. Clean methodology record ✅

**Every one of the 36 stories has a design, a plan and a retrospective.** Verified by
enumeration, not assumed. Three gaps found during the completion pass were closed: two were
false positives (a stray duplicate directory, and one story that shares its design with the
other half of a deliberately split pair), and two were real and reconstructed with explicit
RETROACTIVE banners rather than fabricated as prospective documents.

Nine epic retrospectives. **12 ADRs**, each recording rejected alternatives and why.

### 4. Reproducible datasets ✅

**This was false until 2026-08-20.** Two independent defects broke it:

- **BUG-05 (S1):** scoring was non-deterministic under a fixed seed. `add_many` discarded the
  generator's reproducible client id, and two consumers applied seeded or positional
  operations along an axis ordered by the resulting random key. *A seeded draw applied along
  an unseeded axis is not seeded.* Fixed under **ADR-011**.
- **BUG-04 (S2):** a pinned `reference_date` crashed on persist, so every scenario silently
  resolved its anchor to `date.today()` — the bug was guaranteeing the non-reproducibility
  the field exists to prevent.

Both fixed and regression-tested. Identical parameters now produce an identical portfolio,
and the property holds on PostgreSQL as well as SQLite.

### 5. Human always in the loop ✅

No communication is sendable without explicit operator action. Drafts are persisted as
`DRAFT`; sending is a separate `PATCH …/send` that returns 409 for anything not in draft
status. There is no code path from generation to sent. Every draft and send now records
operator, model, prompt version and timestamps (**NFR-06**, implemented as BUG-08).

---

## Requirements

**All 7 functional requirements delivered.** **All 6 non-functional requirements met and
tested** — NFR-01 demonstrability, NFR-02 performance (measured: 0.222 s priority queue at 500
clients / 2,073 invoices against a 3 s budget), NFR-03 bilingual (177/177 key parity), NFR-04
PWA, NFR-05 accessibility (10-component axe scan, 0 violations), NFR-06 auditability.

A correlation worth recording: **every NFR that had a verifying test was met, and the one that
did not have a test — NFR-06 — was the one not implemented.** Six for six.

## Delivery

| | |
|---|---|
| Epics | **7, all closed and tagged** |
| Stories | 36, each with design, plan, retrospective |
| ADRs | 12 |
| Bugfix pipelines | 7 (BUG-01 … BUG-09, two numbers unused) |
| Commits | 540 |
| Backend | 78 modules, **571 tests** |
| Frontend | 80 modules, **207 tests** |
| Migrations | 6 |
| CI | 3 jobs green — frontend, backend, **backend on real PostgreSQL** |

## What the completion pass found

The project was reported complete at 5 of 5 stories in E6 and 4 of 4 in E7. Running the demo
path and enumerating the PRD found **nine defects**, five of them severity S1 or S0, all
invisible to a green suite:

| Bug | Sev | Finding |
|---|---|---|
| BUG-01 | S1 | Production build red for 13 days; CI red on every push and normalised |
| BUG-02 | S2 | `?category=` matched nothing in any casing — hidden by a loop asserting nothing when empty |
| BUG-03 | S1 | CSV scenarios unusable — a status literal no consumer recognised |
| BUG-04 | S2 | Reproducibility parameter crashed on use |
| BUG-05 | S1 | Scoring non-deterministic under a fixed seed, for four epics |
| BUG-07 | S3 | `format:check` in the manifest, absent from CI |
| BUG-08 | S2 | NFR-06 unimplemented — the only NFR nothing tested |
| **BUG-09** | **S0** | **The backend could not write to its own production database** |

They share one shape: **the test observed a proxy for the outcome rather than the outcome.** A
gate nobody ran. A loop over an empty list. A feature tested only up to persistence. A codepath
behind an optional field. Components each verifiably seeded while their composition was not.
The word "audit" in a scope document. And a schema declared twice, in an environment where the
difference could not be expressed.

**BUG-09 is the argument for M4.** E6 declared its integration checkpoint mandatory because
"E4's M4 caught a generation-layer bug no unit test saw, and E5's M4 repeated the lesson." M4
was then deferred six times, each deferral citing the previous one's blocker without re-testing
it. When it finally ran — against a PostgreSQL started in userspace, needing no root and taking
four minutes — it found on its first execution that the product did not work. 563 tests, mypy,
ruff, CI and `alembic upgrade head` had all been passing. *Creating a schema is not writing to
it.*

Both mechanisms are now closed, not just the defects: `tests/test_schema_agreement.py` diffs
the live migrated schema against the ORM, and a `backend-postgres` CI job runs the full path
against a real database on every push.

## Open, and not blocking

- **The TSU-DSM six-item grouping** needs confirmation (outcome 2 above).
- **Policy questions for Gustavo**, standing since E4: sector as a segmentation dimension
  (structurally impossible — `Sector` is a `Scenario` attribute), the two recovery-rate
  definitions, maximise-recovery vs prevent-write-offs in queue ordering, and — the one worth
  acting on — **no collections practitioner has read the Spanish copy**, which now includes
  LLM-generated director-facing narratives.
- **RaiSE tooling**: `rai gate check` exits 0 while reporting failures; `rai pattern add`
  writes nothing while reporting success; `rai graph query` has been broken for four epics.
  All filed in `dev/parking-lot.md` and worth reporting upstream.

## Scope boundaries, unchanged

Demonstrative only — no real client data, no production deployment, all datasets synthetic.
