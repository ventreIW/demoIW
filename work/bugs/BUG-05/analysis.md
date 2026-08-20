# BUG-05: analysis

## Method: Hypothesis-driven elimination by bisection

Five candidate stages could inject variance. Each was tested independently.

| # | Hypothesis | Test | Result | Conclusion |
|---|---|---|---|---|
| 1 | The generator is non-deterministic | Build two `ProceduralGenerator`s with seed 42 in-process; compare ids, patterns, names | `ids_same=True patterns_same=True names_same=True` | **eliminated** |
| 2 | Scoring is non-deterministic | Generate once; call `/prioritized` twice on the same scenario | `identical=True` (66 vs 66 cases) | **eliminated** |
| 3 | The train/test split varies | Read `_split_by_client` | `sorted(y.unique())`, seeded permutation, `sorted()` outputs | **eliminated** |
| 4 | The estimator is stochastic | Read `sklearn_scorer.py` | `LogisticRegression(max_iter, C)`, default solver `lbfgs` — deterministic | **eliminated** |
| 5 | Identity changes between generation and scoring | Compare the generator's 100 ids against the persisted ids | **`intersection = 0`** | **confirmed** |

Hypotheses 1 and 2 together localise the defect precisely: the generator is reproducible, and
scoring is reproducible *given fixed persisted data*. The variance is injected between them.

An earlier comparison appeared to show differing scores; that was an artefact of comparing
`/prioritized` results positionally when the endpoint returns cases **ranked by priority**. Once
compared per `client_id`, every overlapping client scored identically (`n_score_diffs=0`) — the
intersection was simply empty, because the ids themselves are random.

## Root cause

**The persistence layer discards the reproducible identity the domain layer deliberately
produced.**

`SQLAlchemyClientRepository.add_many` does:

    orm = client_domain_to_orm(client)
    orm.id = str(uuid4())          # "Ensure a new UUID is assigned server-side"

overwriting an id that three separate places in the codebase go out of their way to make
reproducible:

- `procedural_generator.py:56-58` — `_uuid()` draws from the seeded RNG, with the docstring
  "Deterministic UUID drawn from the seeded RNG", and the module docstring explaining it is
  "seeded ... (not ``uuid.uuid4``) so identity is reproducible too".
- `generate_dataset.py:73` — `id=UUID(record["id"])  # use original client id as id in Client
  object`.
- `client_domain_to_orm` — faithfully maps `id=str(domain.id)`.

The mapper preserves it and the very next line throws it away.

## How a random id becomes a different model

The id is not merely a label here — it is the **ordering key for a seeded random draw**:

    # outcome_labeller.py
    clients = clients.sort_values("id").reset_index(drop=True)
    rng     = np.random.default_rng(self._seed)
    scales  = clients["payment_history_pattern"].map(lambda v: PATTERN_PROFILES[v].late_days_mean)
    days_to_collect = rng.exponential(scale=scales.to_numpy())

`rng` is seeded, so it emits the *same sequence of draws* every run. But `scales` is ordered by
`id`, and the ids are now random — so the same draw sequence is applied to a **randomly
permuted list of clients** each time. Client X gets the first draw in one run and the fortieth
in the next.

Different draws → different labels → a different training set → a different fitted model →
different scores, different categories, and a different Pareto subset.

This is why the defect is intermittent rather than constant: two random permutations sometimes
produce label sets close enough that the fitted model lands in the same place (runs 1 and 2
both gave `{'high': 66}`), and sometimes do not (run 3 gave `{'high': 61, 'medium': 5}`).

## Why the seeded RNG made it invisible

Every individual component is correctly seeded, and each can be shown to be deterministic in
isolation — which is exactly what makes this hard to see. The non-determinism lives in the
*coupling*: a seeded draw is applied along an axis whose order is not seeded. Auditing
`np.random` usage, which is the obvious first move, finds nothing wrong and actively
reassures.

## Blast radius beyond scoring

`add` and `add_many` are the same pattern, and `SqlAlchemyScenarioRepository.add` does it too
(`orm.id = str(uuid4())`). Any invariant that depends on stable identity across a
generate/persist boundary is affected, not only labelling.

Note also the interaction with BUG-04: because a pinned `reference_date` previously crashed,
every scenario resolved its anchor to `date.today()`. So reproducibility was broken along two
independent axes at once — identity and calendar — and fixing only one would not have produced
a reproducible pipeline.

## Fix approach — a design decision, not a mechanical change

The obvious fix (delete the overwrite so the domain id is honoured) **breaks a working
behaviour**: two generations with the same seed would then produce identical client UUIDs and
collide on `ClientORM.id`, the primary key. Generating the same seed twice is currently legal
and is exercised by the existing suite.

Namespacing the id per scenario does not help either: the scenario's own id is random, so any
id derived from it is random, and the sort order stays random.

The ordering must therefore stop depending on the surrogate key. Options are recorded in
`plan.md`; the choice is an ADR-level decision about which layer owns identity, and is being
put to the team rather than settled here.
