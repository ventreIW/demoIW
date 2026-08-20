"""s7.4 — the full demo path, end to end, in one run (B-16, NFR-01).

E7's brief promises the demo flow is "proven to work without assistance". This is that
proof. It drives every step a presenter performs, in order, and fails naming the step that
broke.

Two design constraints are load-bearing:

* **Nothing may pass over an empty collection.** BUG-02 hid for four epics behind a loop that
  asserted nothing when the list was empty. A smoke test that passes because nothing happened
  is worse than no smoke test, so every collection is asserted non-empty *before* iteration.

* **The Postgres run must skip loudly, never silently.** E6's M4 survived five stories by
  being quietly deferred. If PostgreSQL is unreachable this file skips with a reason that
  names M4 — it never reports success for something it did not verify.

The path helper is written once and shared by the SQLite and PostgreSQL runs, so the two
cannot drift apart.
"""

import time
from dataclasses import dataclass, field

import pytest
from httpx import AsyncClient

from app.container import get_llm_port
from app.domain.exceptions import ExternalServiceError
from app.main import app
from app.ports.llm_port import ILLMPort

#: NFR-01 — the presenter's budget for the whole demo. The automated path runs in seconds;
#: asserting the real requirement keeps the test meaningful without being flaky.
NFR_01_BUDGET_SECONDS = 600.0

GENERATION = {
    "seed": 42,
    "sector": "retail",
    "client_count": 100,
    "invoice_volume": 5.0,
    "amount_mean": 10000.0,
    "amount_std": 3000.0,
    # Pinned so the calendar is fixed too (BUG-04). With identity fixed by BUG-05 and the
    # calendar fixed here, the path is fully reproducible.
    "reference_date": "2026-06-01",
}


class _NoLLM(ILLMPort):
    """Stub LLM, mirroring test_e2e_intelligence_path.

    Deliberately raises rather than returning canned text: the comms and NL-query steps must
    exercise the real degradation contract s6.0 hardened, not a happy path that never occurs
    when the free tier is exhausted.
    """

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise ExternalServiceError("no LLM in the demo-path E2E")

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        raise ExternalServiceError("no LLM in the demo-path E2E")


@dataclass
class DemoPathResult:
    """What the path produced, for assertions that span steps."""

    scenario_id: str = ""
    elapsed_seconds: float = 0.0
    scores: list[float] = field(default_factory=list)
    category_tally: dict[str, int] = field(default_factory=dict)
    steps_completed: list[str] = field(default_factory=list)


def _fail(step: str, response, extra: str = "") -> str:
    return (
        f"demo path broke at step '{step}': HTTP {response.status_code} "
        f"{response.text[:300]}{(' — ' + extra) if extra else ''}"
    )


async def _run_demo_path(client: AsyncClient) -> DemoPathResult:
    """Drive the whole presenter path once. Every failure names its step."""
    result = DemoPathResult()
    started = time.monotonic()

    # 1 — generate the scenario
    response = await client.post("/api/v1/scenarios/generate", json=GENERATION)
    assert response.status_code == 201, _fail("generate", response)
    generated = response.json()
    assert generated["client_count"] == GENERATION["client_count"], (
        f"generate produced {generated['client_count']} clients, "
        f"expected {GENERATION['client_count']}"
    )
    scenario_id = generated["id"]
    result.scenario_id = scenario_id
    result.steps_completed.append("generate")

    # 2 — activate it (PATCH, not POST — verified against the live schema)
    response = await client.patch(f"/api/v1/scenarios/{scenario_id}/activate")
    assert response.status_code == 200, _fail("activate", response)
    assert (
        response.json()["status"] == "active"
    ), f"activate returned status {response.json()['status']!r}, expected 'active'"
    result.steps_completed.append("activate")

    # 3 — score and persist
    response = await client.post(f"/api/v1/scenarios/{scenario_id}/score")
    assert response.status_code == 201, _fail("score", response)
    scored = response.json()
    assert scored["scored_count"] > 0, f"score persisted nothing: {scored}"
    result.steps_completed.append("score")

    # 4 — the operator's priority queue
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    assert response.status_code == 200, _fail("prioritized", response)
    portfolio = response.json()
    cases = portfolio["cases"]
    assert cases, "prioritized returned an empty queue — nothing for the operator to work"
    assert portfolio["pareto_subset"], "prioritized returned an empty Pareto subset"
    assert portfolio["value_share"] >= portfolio["threshold"], (
        f"Pareto subset holds {portfolio['value_share']} of value, "
        f"below the {portfolio['threshold']} threshold"
    )
    for case in cases:
        assert case["client_name"], "a queue row has no client name"
        assert case["client_name"] != case["client_id"], "client_name is a raw UUID"

    result.scores = sorted(round(case["score"], 9) for case in cases)
    tally: dict[str, int] = {}
    for case in cases:
        tally[case["category"]] = tally.get(case["category"], 0) + 1
    result.category_tally = tally
    result.steps_completed.append("prioritized")

    # 5 — filter the queue by category (the BUG-02 path)
    for category, expected in tally.items():
        response = await client.get(
            f"/api/v1/scenarios/{scenario_id}/prioritized?category={category}"
        )
        assert response.status_code == 200, _fail(f"filter:{category}", response)
        filtered = response.json()["cases"]
        assert (
            len(filtered) == expected
        ), f"?category={category} returned {len(filtered)} cases, expected {expected}"
    result.steps_completed.append("filter")

    # 6 — open the top case
    top_case = cases[0]
    client_id = top_case["client_id"]
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/clients/{client_id}")
    assert response.status_code == 200, _fail("case detail", response)
    detail = response.json()
    assert detail["client"], "case detail has no client profile"
    assert detail["invoices"], "case detail shows no invoices — nothing to collect on"
    result.steps_completed.append("case_detail")

    # 7 — record a contact result (triggers the rescore)
    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/contact-result",
        json={
            "scenario_id": scenario_id,
            "client_id": client_id,
            "contact_result": "promise_to_pay",
            "notes": "s7.4 demo path",
        },
    )
    assert response.status_code == 201, _fail("contact result", response)
    rescored = response.json()
    assert rescored["portfolio"]["cases"], "rescore returned an empty portfolio"
    result.steps_completed.append("contact_result")

    # 8 — generate a communication draft. The LLM is stubbed to fail, so this asserts the
    # degradation contract rather than a happy path that will not exist on an exhausted key.
    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )
    assert response.status_code in (201, 502), _fail(
        "communication draft", response, "expected 201 (drafted) or 502 (LLM degraded)"
    )
    if response.status_code == 201:
        draft = response.json()
        assert draft["draft_text"].strip(), "communication draft is empty"
        assert draft["channel"] == "email"
    result.steps_completed.append("communication")

    # 9 — the executive dashboard
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")
    assert response.status_code == 200, _fail("kpis", response)
    kpis = response.json()
    assert kpis["total_outstanding"] > 0, f"KPIs report nothing outstanding: {kpis}"
    assert kpis["scored_at"], "KPIs carry no scored_at — staleness would be invisible"
    assert kpis["cases_by_category"], "KPIs carry no category breakdown"
    result.steps_completed.append("kpis")

    # 10 — the natural-language question (the demo's headline moment)
    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/query",
        json={"question": "¿Cuánto se debe por categoría de score?"},
    )
    assert response.status_code == 200, _fail("nl query", response)
    answer = response.json()
    assert "answerable" in answer, f"NL query response has no answerable field: {answer}"
    if answer["answerable"]:
        assert answer["result"], "answerable query returned no result payload"
        assert answer["scenario"], "answerable query cites no scenario"
    else:
        # A refusal is a valid outcome with the LLM stubbed out, but it must be a
        # *structured* refusal carrying the supported vocabulary (s6.3/s6.4 contract).
        assert answer["reason"], "unanswerable query gave no reason"
        assert answer["supported"], "refusal carried no supported vocabulary"
    result.steps_completed.append("nl_query")

    result.elapsed_seconds = time.monotonic() - started
    return result


@pytest.fixture
def _stub_llm():
    """Override the LLM port for the duration of a test."""
    app.dependency_overrides[get_llm_port] = lambda: _NoLLM()
    yield
    app.dependency_overrides.pop(get_llm_port, None)


@pytest.mark.anyio
async def test_full_demo_path(client: AsyncClient, _stub_llm) -> None:
    """AC1, AC3, AC4 — every step of the demo runs, in order, inside the NFR-01 budget."""
    result = await _run_demo_path(client)

    assert result.steps_completed == [
        "generate",
        "activate",
        "score",
        "prioritized",
        "filter",
        "case_detail",
        "contact_result",
        "communication",
        "kpis",
        "nl_query",
    ], f"the path did not complete every step: {result.steps_completed}"

    assert result.elapsed_seconds < NFR_01_BUDGET_SECONDS, (
        f"demo path took {result.elapsed_seconds:.1f}s, "
        f"over the NFR-01 budget of {NFR_01_BUDGET_SECONDS:.0f}s"
    )
    print(
        f"\n[s7.4] demo path completed in {result.elapsed_seconds:.2f}s "
        f"(NFR-01 budget {NFR_01_BUDGET_SECONDS:.0f}s) — "
        f"{len(result.scores)} cases, categories {result.category_tally}"
    )


class _ScriptedLLM(ILLMPort):
    """A deterministic, well-formed LLM.

    `_NoLLM` proves the path degrades correctly; it cannot prove the path *works*. With the
    LLM always failing, the demo's headline moment — a question answered with a chart, a
    narrative and a citation — is never exercised. This stub returns the real contract shapes
    (a QueryIntent JSON object for `query`, prose after the RESPUESTA: marker for the
    narrative, and draft copy for `generate`) so the success path is verified without a
    network call or a free-tier request.

    Values are taken from the source enums, not from prose: Metric and Dimension are read
    from app.domain.value_objects.query_intent.
    """

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        """Serves two callers: the comms draft and the NL-query narrator.

        They are distinguished by the prompt itself — `prompts/nl_query/v1_narrate.txt`
        instructs the model to emit a `RESPUESTA:` line and `prompts/communications/
        v1_draft.txt` does not. Keying on that is exact rather than heuristic.

        The narrator reply deliberately includes chain-of-thought *before* the marker,
        reproducing the real failure s6.3 found in live verification: the configured
        reasoning model returned its whole reasoning trace, and every stubbed test passed
        because a stub returns whatever prose it was handed. Emitting the noise here means
        this test asserts the marker extraction actually strips it.
        """
        if _ANSWER_MARKER in prompt:
            return (
                "Necesito redactar un párrafo breve en español para el director. "
                "Veamos: el total es alto y se concentra en una categoría. "
                "Redactemos algo conciso...\n"
                f"{_ANSWER_MARKER} La mayor parte del saldo pendiente se concentra en la "
                "categoría de alta cobrabilidad."
            )
        return (
            "Estimado cliente,\n\n"
            "Le escribimos para recordarle el saldo pendiente de su cuenta. "
            "Agradeceríamos su pronta atención.\n\n"
            "Atentamente,\nEl equipo de cobranza"
        )

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        """The translation pass: a QueryIntent as JSON.

        Values come from the source enums (Metric, Dimension in
        app.domain.value_objects.query_intent), not from prose. QueryIntent forbids extra
        keys by design (ADR-008), so an invented field here would be refused.
        """
        return '{"metric": "outstanding", "group_by": "score_category", "filters": []}'


#: Marker the narrate prompt requires before the final paragraph (answer_nl_query.py:217).
_ANSWER_MARKER = "RESPUESTA:"


@pytest.fixture
def _scripted_llm():
    app.dependency_overrides[get_llm_port] = lambda: _ScriptedLLM()
    yield
    app.dependency_overrides.pop(get_llm_port, None)


@pytest.mark.anyio
async def test_demo_headline_moment_succeeds(client: AsyncClient, _scripted_llm) -> None:
    """The two LLM-backed steps must be provable on their SUCCESS path, not only degraded.

    A demo-readiness test that only ever sees the LLM fail proves the product does not crash.
    It does not prove the demo works. This drives the comms draft and the NL query with a
    well-formed model and asserts the presenter-visible outcome.
    """
    response = await client.post("/api/v1/scenarios/generate", json=GENERATION)
    assert response.status_code == 201, _fail("generate", response)
    scenario_id = response.json()["id"]

    await client.patch(f"/api/v1/scenarios/{scenario_id}/activate")
    assert (await client.post(f"/api/v1/scenarios/{scenario_id}/score")).status_code == 201

    queue = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    cases = queue.json()["cases"]
    assert cases, "empty queue — the headline-moment assertions would be vacuous"
    client_id = cases[0]["client_id"]

    # The operator's moment: an editable, non-empty draft.
    drafted = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )
    assert drafted.status_code == 201, _fail("communication draft (scripted)", drafted)
    draft = drafted.json()
    assert draft["draft_text"].strip(), "scripted LLM produced an empty draft"
    assert draft["status"], "draft carries no status — the audit trail would be blank"

    # The director's moment: chart data, a narrative, and a citation.
    answered = await client.post(
        f"/api/v1/scenarios/{scenario_id}/query",
        json={"question": "¿Cuánto se debe por categoría de score?"},
    )
    assert answered.status_code == 200, _fail("nl query (scripted)", answered)
    answer = answered.json()
    assert (
        answer["answerable"] is True
    ), f"the headline query was refused with a well-formed model: {answer}"
    assert answer["result"]["series"], "answerable query returned no chart series"
    assert answer["result"]["metric"] == "outstanding"
    assert answer["scenario"], "the answer cites no scenario — provenance would be missing"
    narrative = answer.get("narrative")
    assert narrative, (
        "the headline query produced no narrative with a well-formed model — "
        "the director would see a chart with no explanation"
    )
    # The scripted reply deliberately prefixes chain-of-thought before the marker.
    # s6.3 shipped a live bug where exactly that reasoning trace reached the director.
    assert (
        "Redactemos algo conciso" not in narrative
    ), f"the model's reasoning trace leaked into the director-facing narrative: {narrative!r}"
    assert narrative.startswith(
        "La mayor parte"
    ), f"marker extraction returned the wrong span: {narrative!r}"
    print(
        f"\n[s7.4] headline moment OK — metric={answer['result']['metric']} "
        f"group_by={answer['result']['group_by']} "
        f"series={len(answer['result']['series'])} narrative={narrative[:60]!r}"
    )


@pytest.mark.anyio
async def test_demo_path_is_repeatable(client: AsyncClient, _stub_llm) -> None:
    """AC5 — the demo must give the same answer twice (BUG-05, ADR-011).

    Asserted at the demo level rather than the unit level on purpose: what matters to a
    presenter is that rehearsing the demo predicts the demo, and that a director asking the
    same question twice is not shown two different portfolios.

    Client ids are random surrogate keys by design, so the comparison is over portfolio
    *content* — the score multiset and the category tally — not over identity.
    """
    first = await _run_demo_path(client)
    second = await _run_demo_path(client)

    assert first.scores, "empty portfolio — the repeatability comparison would be vacuous"

    assert first.category_tally == second.category_tally, (
        f"the same seed produced different category distributions across two runs: "
        f"{first.category_tally} vs {second.category_tally}"
    )
    assert len(first.scores) == len(second.scores), (
        f"the same seed produced portfolios of different sizes: "
        f"{len(first.scores)} vs {len(second.scores)}"
    )
    assert first.scores == second.scores, "the same seed produced different scores"


@pytest.mark.anyio
async def test_csv_upload_limit_is_explicit(client: AsyncClient) -> None:
    """AC7 — CSV upload is exercised to its real limit, and the limit is asserted.

    B-07/RF-07 ships CSV upload, and the demo may show it. It works up to persistence and
    then stops: BUG-06 means an uploaded scenario cannot be scored, because create_from_csv
    assigns PaymentPattern.ON_TIME to every client (a CSV carries no payment history), so the
    labeller draws a single class and training aborts.

    Asserting the boundary rather than omitting the step keeps the gap visible in the
    demo-readiness signal. This test will start failing when BUG-06 is fixed, which is the
    intended signal to widen it.
    """
    rows = "\n".join(
        f"Client {i:02d},{1000 + i * 137}.00,2026-01-{(i % 28) + 1:02d},INV-{i:03d}"
        for i in range(30)
    )
    csv = "client_name,amount,due_date,invoice_id\n" + rows + "\n"

    upload = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("demo.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert upload.status_code == 201, _fail("csv upload", upload)
    scenario_id = upload.json()["id"]
    assert (
        upload.json()["client_count"] == 30
    ), f"CSV upload persisted {upload.json()['client_count']} clients, expected 30"

    # It is listed and readable — the parts of the demo that do work.
    listed = await client.get("/api/v1/scenarios")
    assert listed.status_code == 200
    assert any(
        s["id"] == scenario_id for s in listed.json()
    ), "the uploaded scenario does not appear in the scenario list"

    detail = await client.get(f"/api/v1/scenarios/{scenario_id}")
    assert detail.status_code == 200, _fail("uploaded scenario detail", detail)

    # And here is the wall. KPIs decline cleanly with a 409 rather than crashing.
    kpis = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")
    assert kpis.status_code == 409, (
        f"BUG-06 boundary moved: /kpis on an uploaded scenario returned "
        f"{kpis.status_code}, expected 409 (no persisted scores). "
        f"If BUG-06 is fixed, widen this test to drive the full path on CSV data."
    )


# ---------------------------------------------------------------------------
# E6 M4 — the same path, against the real driver.
#
# Open across E4, E5, s6.2, s6.3, s6.4 and now E7. Everything above runs on SQLite via
# `Base.metadata.create_all`, so neither asyncpg nor a single Alembic migration is exercised
# by any other test in this project. These two close that gap — or skip loudly saying they
# did not.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_full_demo_path_on_postgres(postgres_client: AsyncClient, _stub_llm) -> None:
    """AC6, AC10, AC11 — the demo path on real PostgreSQL with migrations from zero.

    Invokes the *same* `_run_demo_path` helper as the SQLite test (AC10) so the two runs
    cannot drift. What differs is everything underneath: asyncpg instead of aiosqlite, real
    Postgres type coercion, real foreign-key enforcement, and a schema built by Alembic rather
    than by `create_all`.

    E4's M4 caught a generation-layer bug no unit test saw. This is the same instrument.
    """
    result = await _run_demo_path(postgres_client)

    assert result.steps_completed == [
        "generate",
        "activate",
        "score",
        "prioritized",
        "filter",
        "case_detail",
        "contact_result",
        "communication",
        "kpis",
        "nl_query",
    ], f"the path did not complete on PostgreSQL: {result.steps_completed}"

    assert result.elapsed_seconds < NFR_01_BUDGET_SECONDS, (
        f"demo path on PostgreSQL took {result.elapsed_seconds:.1f}s, "
        f"over the NFR-01 budget of {NFR_01_BUDGET_SECONDS:.0f}s"
    )
    print(
        f"\n[s7.4 · M4] demo path on real PostgreSQL completed in "
        f"{result.elapsed_seconds:.2f}s — {len(result.scores)} cases, "
        f"categories {result.category_tally}"
    )


@pytest.mark.anyio
async def test_demo_path_is_repeatable_on_postgres(postgres_client: AsyncClient, _stub_llm) -> None:
    """BUG-05's guarantee must hold on the real driver too.

    Reproducibility depends on `generation_index` (migration 0004) being persisted and
    ordered correctly. On SQLite that column comes from `create_all`; here it comes from the
    migration, which is the only place its DDL and backfill are ever executed.
    """
    first = await _run_demo_path(postgres_client)
    second = await _run_demo_path(postgres_client)

    assert first.scores, "empty portfolio on PostgreSQL — the comparison would be vacuous"
    assert first.category_tally == second.category_tally, (
        f"the same seed produced different distributions on PostgreSQL: "
        f"{first.category_tally} vs {second.category_tally}"
    )
    assert first.scores == second.scores, "the same seed produced different scores on PostgreSQL"


def test_migrations_roundtrip_on_a_clean_database() -> None:
    """Every migration must apply from zero and reverse cleanly.

    Three of the six have never run anywhere until today: 0004 (BUG-05's `generation_index`,
    whose backfill uses `ROW_NUMBER() OVER (PARTITION BY scenario_id ORDER BY id)`), 0005
    (BUG-08's audit columns) and 0006 (BUG-09's nullability fix). A migration that cannot be
    rolled back is a migration nobody can safely deploy.

    Runs on an empty schema deliberately. Downgrades are only obliged to be safe on data the
    forward migration could have produced, and 0006 relaxes a constraint that real rows
    legitimately violate — re-imposing it over such rows *should* fail rather than delete
    them. That is a data-safety property, not a reversibility one.
    """
    import sqlalchemy as sa

    from tests.conftest import _postgres_url, _run_alembic

    url = _postgres_url()
    sync_url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = sa.create_engine(sync_url)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
    engine.dispose()

    _run_alembic(url, "upgrade head")
    _run_alembic(url, "downgrade base")
    _run_alembic(url, "upgrade head")
