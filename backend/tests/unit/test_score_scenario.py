"""Tests for the ScoreScenario use case (s4.3 T4).

Composes build → fit → score → categorize into `Score` entities. Persistence is
deliberately absent: `IScoreRepository` is s4.9 (Nano) and unmerged, so this use
case returns entities and the repository call is the only deferred piece.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pandas as pd
import pytest

from app.application.use_cases.score_scenario import ScoreScenario
from app.domain.enums import ScoreCategory
from app.domain.exceptions import InsufficientTrainingDataError
from app.domain.value_objects.raw_dataset import RawDataset
from app.domain.value_objects.scoring_result import EvaluationStatus

_PATTERNS = ["on_time", "delayed_30", "delayed_60", "delayed_90_plus", "partial", "default"]

#: Settled-only clients get ids from a distinct range so exclusion is assertable.
_SETTLED_ID_BASE = 100_000


def _dataset(size: int = 200, settled_ratio: float = 0.0) -> RawDataset:
    """Clients with open invoices, plus an optional fully-settled cohort."""
    due = datetime.fromisoformat("2026-05-01")
    clients, invoices, payments = [], [], []

    for i in range(size):
        cid = str(UUID(int=i))
        clients.append(
            {
                "id": cid,
                "name": f"Empresa {cid}",
                "sector": "retail",
                "payment_history_pattern": _PATTERNS[i % len(_PATTERNS)],
            }
        )
        invoices.append(
            {
                "id": f"i{i:04d}",
                "client_id": cid,
                "folio": f"INV-{i}",
                "amount": 1000.0 + i,
                "issue_date": due,
                "due_date": due,
                "days_overdue": 10 + (i % 90),
                "status": "overdue",
            }
        )

    settled_count = int(size * settled_ratio)
    for j in range(settled_count):
        cid = str(UUID(int=_SETTLED_ID_BASE + j))
        clients.append(
            {"id": cid, "name": "S", "sector": "retail", "payment_history_pattern": "on_time"}
        )
        invoices.append(
            {
                "id": f"si{j:04d}",
                "client_id": cid,
                "folio": f"INV-S{j}",
                "amount": 500.0,
                "issue_date": due,
                "due_date": due,
                "days_overdue": 0,
                "status": "paid",
            }
        )
        payments.append(
            {"id": f"p{j}", "invoice_id": f"si{j:04d}", "amount": 500.0, "paid_date": due}
        )

    return RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(payments)
        if payments
        else pd.DataFrame(columns=["id", "invoice_id", "amount", "paid_date"]),
    )


def test_every_scoreable_client_gets_a_score_entity() -> None:
    dataset = _dataset(200)
    scenario_id = uuid4()

    result = ScoreScenario().execute(dataset, scenario_id=scenario_id, seed=42)

    assert len(result.scores) == 200
    for score in result.scores:
        assert 0.0 <= score.score_value <= 100.0
        assert score.category in set(ScoreCategory)
        assert score.scenario_id == scenario_id
        assert score.explanation


def test_unscored_clients_are_counted_not_defaulted() -> None:
    """A 0 would read as 'certain not to collect'. Absence is not zero."""
    dataset = _dataset(200, settled_ratio=0.25)

    result = ScoreScenario().execute(dataset, scenario_id=uuid4(), seed=42)

    assert result.unscored_client_count == 50
    assert len(result.scores) == 200
    settled_ids = {UUID(int=_SETTLED_ID_BASE + j) for j in range(50)}
    assert not settled_ids & {s.client_id for s in result.scores}


def test_evaluation_is_attached() -> None:
    result = ScoreScenario().execute(_dataset(300), scenario_id=uuid4(), seed=42)

    assert result.evaluation.status in set(EvaluationStatus)
    assert result.evaluation.majority_baseline > 0.0


def test_too_small_scenario_raises_naming_counts() -> None:
    with pytest.raises(InsufficientTrainingDataError) as excinfo:
        ScoreScenario().execute(_dataset(6), scenario_id=uuid4(), seed=42)

    message = str(excinfo.value)
    assert "at least" in message
    assert "6" in message


def test_scores_are_reproducible_for_a_seed() -> None:
    dataset = _dataset(200)
    scenario_id = uuid4()

    first = ScoreScenario().execute(dataset, scenario_id=scenario_id, seed=42)
    second = ScoreScenario().execute(dataset, scenario_id=scenario_id, seed=42)

    assert [s.score_value for s in first.scores] == [s.score_value for s in second.scores]


def test_categories_follow_the_documented_thresholds() -> None:
    result = ScoreScenario().execute(_dataset(300), scenario_id=uuid4(), seed=42)

    for score in result.scores:
        if score.score_value < 40.0:
            assert score.category is ScoreCategory.LOW
        elif score.score_value > 70.0:
            assert score.category is ScoreCategory.HIGH
        else:
            assert score.category is ScoreCategory.MEDIUM


def test_no_repository_is_imported() -> None:
    """s4.9 owns persistence; this use case must not reach for a repository.

    Checks the module's resolved imports rather than its source text — the
    docstring legitimately mentions IScoreRepository to explain the deferral.
    """
    import ast
    import inspect

    from app.application.use_cases import score_scenario

    tree = ast.parse(inspect.getsource(score_scenario))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)

    assert not [name for name in imported if "repositor" in name.lower()]
