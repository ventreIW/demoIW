"""End-to-end scoring on real generated scenarios (s4.3 T5).

**This is E4's M1 go/no-go.** If the AUC gate fails here, the correct response is
to revise ADR-007 — not to tune the model, swap the estimator, or lower the gate.
s4.4 (explanation), s4.5 (prioritization) and s4.6 (rescore) all rest on this
number meaning something.

The gate is two-part, because a single scenario's AUC carries real sampling noise:
a per-run floor that catches a broken model, and a mean across seeds that is the
actual quality signal. Measured at C=0.01 over 45 configurations (3 sectors ×
3 sizes × 5 seeds): per-run minimum 0.577, means 0.732–0.739.

Retail is consistently weakest — its pattern mix carries the highest `partial`
weight, and partial payers sit mid-gradient, so the classes overlap more. The
mean-AUC test therefore runs on retail rather than an easier sector.
"""

from uuid import uuid4

import pandas as pd
import pytest

from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.use_cases.score_scenario import ScoreScenario
from app.domain.enums import ScoreCategory, Sector
from app.domain.value_objects.generation_params import GenerationParams
from app.domain.value_objects.scoring_result import EvaluationStatus

_REFERENCE_DATE = pd.Timestamp("2026-07-01").date()

#: Per-run floor. A single scenario's AUC carries real sampling noise, so this is
#: deliberately below the measured minimum (0.577 across 45 configurations) with a
#: small margin. It catches a genuinely broken model, not an unlucky seed.
#: **Do not lower this to make a red build pass.**
AUC_FLOOR = 0.55

#: The real signal: mean across seeds. Measured 0.732-0.739 at C=0.01, so this has
#: a large margin and would fail loudly if the model actually degraded.
AUC_MEAN_GATE = 0.65


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


# --- The go/no-go ---------------------------------------------------------


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_auc_above_gate_on_real_scenarios(sector: Sector) -> None:
    """M1 GO/NO-GO. A failure here means stop and revise ADR-007."""
    run = ScoreScenario().execute(_scenario(sector=sector), scenario_id=uuid4(), seed=42)

    assert run.evaluation.status is EvaluationStatus.EVALUATED
    assert run.evaluation.roc_auc is not None
    assert run.evaluation.roc_auc >= AUC_FLOOR, (
        f"{sector.value}: ROC-AUC {run.evaluation.roc_auc:.3f} below the {AUC_FLOOR} floor. "
        "Do not lower the floor — revise ADR-007."
    )


def test_mean_auc_across_seeds_above_gate() -> None:
    """The real quality signal — one lucky or unlucky seed is not evidence.

    Retail is the weakest sector (highest `partial` weight, and partial payers sit
    mid-gradient), so this runs on the hardest case.
    """
    aucs = []
    for seed in (1, 7, 42, 99):
        run = ScoreScenario().execute(_scenario(seed=seed), scenario_id=uuid4(), seed=seed)
        assert run.evaluation.roc_auc is not None
        assert run.evaluation.roc_auc >= AUC_FLOOR, f"seed {seed}: {run.evaluation.roc_auc:.3f}"
        aucs.append(run.evaluation.roc_auc)

    mean_auc = sum(aucs) / len(aucs)
    assert mean_auc >= AUC_MEAN_GATE, (
        f"mean ROC-AUC {mean_auc:.3f} across seeds {aucs} is below {AUC_MEAN_GATE}. "
        "This is the gate that matters — revise ADR-007 rather than lowering it."
    )


def test_coefficient_signs_stable_across_seeds() -> None:
    """Regression guard for the collinearity that T5 uncovered.

    At the sklearn default C=1.0 this failed in 19 of 27 configurations, because
    days_overdue_max and days_overdue_mean correlate at 0.872 and the fit split
    their weight arbitrarily. Strong ridge (C=0.01) makes the signs stable.
    """
    from app.adapters.scoring.sklearn_scorer import SklearnScorer
    from app.application.use_cases.build_training_set import BuildTrainingSet

    for seed in (1, 7, 42, 99):
        training_set = BuildTrainingSet().execute(_scenario(seed=seed), seed=seed)
        scorer = SklearnScorer()
        scorer.fit(training_set)
        coefficients = scorer.coefficients()

        assert coefficients["days_overdue_max"] < 0, f"seed {seed} flipped days_overdue_max"
        assert coefficients["pct_invoices_settled"] > 0, f"seed {seed} flipped pct_invoices_settled"


# --- Correctness of the pipeline -----------------------------------------


def test_no_leakage_in_fitted_feature_names() -> None:
    """ADR-006 at the boundary the model actually consumes."""
    from app.adapters.scoring.sklearn_scorer import SklearnScorer
    from app.application.use_cases.build_training_set import BuildTrainingSet

    training_set = BuildTrainingSet().execute(_scenario(), seed=42)
    scorer = SklearnScorer()
    scorer.fit(training_set)

    for name in scorer.coefficients():
        assert "pattern" not in name
        assert not name.startswith("sector")


def test_coefficient_directions_on_real_data() -> None:
    """The canary, against generated data rather than synthetic fixtures."""
    from app.adapters.scoring.sklearn_scorer import SklearnScorer
    from app.application.use_cases.build_training_set import BuildTrainingSet

    training_set = BuildTrainingSet().execute(_scenario(1000), seed=42)
    scorer = SklearnScorer()
    scorer.fit(training_set)
    coefficients = scorer.coefficients()

    assert coefficients["pct_invoices_settled"] > 0
    assert coefficients["days_overdue_max"] < 0


def test_scoring_reproducible_end_to_end() -> None:
    dataset = _scenario()
    scenario_id = uuid4()

    first = ScoreScenario().execute(dataset, scenario_id=scenario_id, seed=42)
    second = ScoreScenario().execute(dataset, scenario_id=scenario_id, seed=42)

    assert [s.score_value for s in first.scores] == [s.score_value for s in second.scores]
    assert first.evaluation.roc_auc == second.evaluation.roc_auc


# --- Output shape ---------------------------------------------------------


def test_category_distribution_is_plausible() -> None:
    """No band may swallow the portfolio — that would make ranking useless."""
    run = ScoreScenario().execute(_scenario(1000), scenario_id=uuid4(), seed=42)

    counts = {category: 0 for category in ScoreCategory}
    for score in run.scores:
        counts[score.category] += 1

    total = len(run.scores)
    for category, count in counts.items():
        assert count / total < 0.90, f"{category.value} holds {count / total:.0%} of the portfolio"

    assert counts[ScoreCategory.MEDIUM] > 0


def test_every_scored_client_has_a_usable_score() -> None:
    run = ScoreScenario().execute(_scenario(), scenario_id=uuid4(), seed=42)

    assert run.scores
    for score in run.scores:
        assert 0.0 <= score.score_value <= 100.0
        assert score.explanation
        assert score.scored_at is not None


def test_unscored_clients_reported_on_real_data() -> None:
    """32-43% of generated clients have nothing outstanding (s4.2 measurement)."""
    run = ScoreScenario().execute(_scenario(400), scenario_id=uuid4(), seed=42)

    assert run.unscored_client_count > 0
    assert run.unscored_client_count + len(run.scores) == 400
