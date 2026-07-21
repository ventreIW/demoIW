"""Score explanations on real generated scenarios (s4.4 T3).

Unit tests prove the rules hold on hand-built inputs. Only running the real
pipeline shows whether the rules produce Spanish a collections officer would
accept — which is why T2's direction-of-framing defect was found by reading
output, not by a test.

The 30% materiality threshold was measured on **retail** alone. These tests run
all three sectors, so a threshold tuned to the wrong distribution surfaces as
visibly odd text rather than a silent skew.
"""

import re
from uuid import uuid4

import pandas as pd
import pytest

from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.use_cases.score_scenario import ScoreScenario
from app.domain.enums import ScoreCategory, Sector
from app.domain.value_objects.generation_params import GenerationParams

_REFERENCE_DATE = pd.Timestamp("2026-07-01").date()

#: Model vocabulary that must never reach an officer.
_FORBIDDEN_TOKENS = [
    "days_overdue",
    "pct_invoices",
    "outstanding_amount",
    "avg_invoice",
    "avg_days_late",
    "invoice_count",
    "has_partial",
    "coef",
    "contribution",
    "feature",
    "logistic",
    "auc",
    "none",
    "nan",
]


def _scenario(client_count: int = 400, sector: Sector = Sector.RETAIL, seed: int = 42):
    params = GenerationParams(
        seed=seed,
        sector=sector,
        client_count=client_count,
        invoice_volume=4.0,
        amount_mean=10_000.0,
        amount_std=3_000.0,
        reference_date=_REFERENCE_DATE,
    )
    return ProceduralGenerator(params).generate()


def _run(sector: Sector = Sector.RETAIL, n: int = 400, seed: int = 42):
    return ScoreScenario().execute(_scenario(n, sector, seed), scenario_id=uuid4(), seed=seed)


# --- Every explanation is usable -----------------------------------------


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_explanations_on_real_scenarios(sector: Sector) -> None:
    run = _run(sector=sector)

    assert run.scores
    for score in run.scores:
        assert score.explanation.strip()
        assert score.explanation.endswith(".")
        lowered = score.explanation.lower()
        for token in _FORBIDDEN_TOKENS:
            assert token not in lowered, f"{token!r} leaked: {score.explanation}"


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_headline_matches_category(sector: Sector) -> None:
    """The prose must not contradict the band shown beside it."""
    run = _run(sector=sector)

    for score in run.scores:
        if score.category is ScoreCategory.LOW:
            assert score.explanation.startswith("Riesgo alto")
        elif score.category is ScoreCategory.HIGH:
            assert score.explanation.startswith("Buen perfil de pago")
        else:
            assert score.explanation.startswith("Perfil mixto")


def test_no_client_gets_ageing_twice() -> None:
    """The measured 26.2% case, at scale on real data.

    'atraso' may appear inside one ageing clause; it must never appear as two
    separate clauses.
    """
    run = _run(n=600)

    for score in run.scores:
        body = score.explanation.split(":", 1)[1]
        clauses = re.split(r",| y ", body)
        ageing_clauses = [c for c in clauses if "atraso" in c or "vencida" in c]
        assert len(ageing_clauses) <= 1, f"ageing stated twice: {score.explanation}"


# --- The threshold is doing work -----------------------------------------


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_factor_count_distribution_is_not_degenerate(sector: Sector) -> None:
    """If every client landed on exactly 3 factors, the threshold would be inert;
    if every client landed on 1, it would be throttling real signal."""
    run = _run(sector=sector, n=600)

    counts = [len(re.split(r",| y ", s.explanation.split(":", 1)[1])) for s in run.scores]
    distinct = set(counts)

    assert len(distinct) > 1, f"{sector.value}: every explanation has {distinct} clauses"
    assert min(counts) == 1, f"{sector.value}: no client got a single-factor explanation"


def test_explanations_are_mostly_distinct() -> None:
    """Templated text still has to discriminate between clients."""
    run = _run(n=600)

    distinct = {s.explanation for s in run.scores}
    assert len(distinct) / len(run.scores) > 0.5


# --- Reproducibility ------------------------------------------------------


def test_explanations_deterministic() -> None:
    dataset = _scenario()

    first = ScoreScenario().execute(dataset, scenario_id=uuid4(), seed=42)
    second = ScoreScenario().execute(dataset, scenario_id=uuid4(), seed=42)

    assert [s.explanation for s in first.scores] == [s.explanation for s in second.scores]


# --- Structural boundary (AC #12) ----------------------------------------


def test_sklearn_not_imported_in_application_or_domain_layers() -> None:
    """s4.3 wrote this rule as prose and it was violated in that same story.

    ``sklearn`` may appear only under ``app/adapters/scoring/``. Anywhere else and
    a modelling library has leaked into the application or domain layer.

    Parsed with ``ast`` rather than grepped: a first cut searched for the string
    "sklearn" and flagged a docstring that *describes* this rule, plus a module
    importing our own ``SklearnScorer`` class. Testing text instead of structure
    fails for the wrong reasons — the same mistake s4.3's retrospective recorded.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / "app"
    allowed = "adapters/scoring"
    offenders: list[str] = []

    for path in root.rglob("*.py"):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(allowed):
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            if any(m == "sklearn" or m.startswith("sklearn.") for m in modules):
                offenders.append(relative)

    assert not offenders, f"sklearn imported outside {allowed}/: {sorted(set(offenders))}"
