# BUG-05: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-05/nondeterministic-scoring` · **From:** `main`
**Found:** while verifying BUG-02, which printed the category tally twice.

WHAT:      Scoring is not reproducible. Two `POST /generate` calls with identical parameters
           (`seed=42`) followed by `GET /prioritized` return different category distributions
           and different portfolios. The seed does not determine the output.

WHEN:      Every pair of generations with the same seed. Observed:
             run 1: {'high': 66}
             run 2: {'high': 66}
             run 3: {'high': 61, 'medium': 5}
           Independent of the BUG-02 fix — reproduces on both sides of it.

WHERE:     `backend/app/adapters/persistence/sqlalchemy_client_repo.py:39` (`add_many`)
             `orm.id = str(uuid4())  # Ensure a new UUID is assigned server-side`
           and the same overwrite at `:25` in `add`.

EXPECTED:  Identical parameters produce an identical portfolio. `GenerationParams` documents
           itself as "Fully determines the output: the same params (including seed and
           reference_date)", and `ProceduralGenerator` states identity is drawn from the
           seeded RNG "not ``uuid.uuid4``, so identity is reproducible too".

Done when: 1. Two generations with identical params yield identical per-client scores and an
              identical category distribution.
           2. The property is covered by a regression test that would fail on today's code.
           3. Generating the same seed twice still works — no primary-key collision.
           4. Full backend suite green; no test weakened or deleted.

TRIAGE:
  Bug Type:    Logic
  Severity:    S1-High
  Origin:      Design
  Qualifier:   Incorrect

  Rationale:
  - Logic: the computation's result depends on a value that should not influence it. Nothing
    is malformed or mistyped; the wrong thing determines the outcome.
  - S1: it invalidates the demo's central claim. s7.4 is a demo smoke test that cannot assert
    stable numbers against this, and the executive panel can answer the same question two
    ways. It also undermines ADR-006/007, whose measured figures (ROC-AUC 0.732–0.739) assume
    a reproducible pipeline.
  - Origin=Design: the persistence layer asserts ownership of identity ("assigned
    server-side") while the domain layer treats identity as reproducible generated data. Both
    positions are internally coherent; the layers were never reconciled. This is not a typo.
  - Qualifier=Incorrect: an id is assigned, and it is the wrong one.

  Jira fields: not set — no backlog adapter configured (`.raise/backlog.yaml` absent).
