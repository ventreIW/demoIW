"""Compose persisted scores and raw invoice data into the executive portfolio view.

Mirrors :mod:`app.application.services.case_aggregate_service`: a module-level async
function over repository ports returning a frozen aggregate, callable from both a
router and a use case. The natural-language query executor (s6.3) is the second
caller, which is what keeps the dashboard and the NL answer from disagreeing
(ADR-008).

**This module never fits a model.** It reads the ``Score`` rows that
``POST /scenarios/{id}/score`` persisted (ADR-009). ``/prioritized`` still re-trains
per request; converging the two is filed for E7/E8, and until then ``scored_at``
travels with the aggregate so a stale dashboard is legible rather than silently
wrong.

Money comes from :func:`app.application.services.feature_extractor.outstanding_by_client`
— imported, never reimplemented. It is already the shared definition of unsettled
balance net of partial payments, and a second one here would drift from the scoring
engine's while both looked plausible.
"""

from uuid import UUID

import pandas as pd

from app.application.services.feature_extractor import outstanding_by_client
from app.domain.entities.score import Score
from app.domain.exceptions import EntityNotFoundError, PortfolioNotScoredError
from app.domain.value_objects.portfolio_kpis import (
    ClientKpiRow,
    PortfolioKpis,
    build_portfolio_kpis,
)
from app.ports.repositories import IScenarioRepository, IScoreRepository

_OPEN_STATUS = "overdue"
_SETTLED_STATUS = "paid"


async def fetch_portfolio_kpis(
    scenario_id: UUID,
    scenario_repo: IScenarioRepository,
    score_repo: IScoreRepository,
) -> PortfolioKpis:
    """Build the portfolio KPI aggregate for a scored scenario.

    Raises:
        EntityNotFoundError: the scenario does not exist.
        PortfolioNotScoredError: the scenario exists but carries no persisted
            scores, or holds no data to aggregate. Refusing is deliberate — see
            ADR-009.
    """
    scenario = await scenario_repo.get_by_id(scenario_id)
    if scenario is None:
        raise EntityNotFoundError("Scenario", str(scenario_id))

    scores = await score_repo.get_by_scenario(scenario_id)
    if not scores:
        raise PortfolioNotScoredError(str(scenario_id))

    dataset = await scenario_repo.get_raw_dataset(scenario_id)
    if dataset is None:
        raise PortfolioNotScoredError(str(scenario_id))

    invoices, payments = dataset.invoices, dataset.payments
    outstanding = outstanding_by_client(invoices, payments)
    ageing = _max_days_overdue_by_client(invoices)

    rows = [
        ClientKpiRow(
            client_id=str(score.client_id),
            # A scored client with everything settled has no entry in either series.
            # Zero is correct here, not a missing-data error: it is a real client
            # with a real score and nothing left to collect.
            outstanding=float(outstanding.get(str(score.client_id), 0.0)),
            score=score.score_value,
            category=score.category,
            days_overdue=int(ageing.get(str(score.client_id), 0)),
        )
        for score in scores
    ]

    return build_portfolio_kpis(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        sector=scenario.sector,
        scored_at=max(score.scored_at for score in scores),
        rows=rows,
        collected_to_date=_collected_to_date(invoices, payments),
        unscored_client_count=_unscored_client_count(dataset.clients, scores),
    )


def _max_days_overdue_by_client(invoices: pd.DataFrame) -> pd.Series:
    """Age of the oldest open invoice per client.

    Maximum rather than mean, matching the rule ``PrioritizedCase`` established for
    the operator queue: a mean flatters a badly aged account by averaging it against
    recent invoices. Two definitions across the two panels would be a defect the
    director finds before we do.
    """
    if invoices.empty:
        return pd.Series(dtype=int)
    open_invoices = invoices[invoices["status"] == _OPEN_STATUS]
    if open_invoices.empty:
        return pd.Series(dtype=int)
    return open_invoices.groupby("client_id")["days_overdue"].max()


def _collected_to_date(invoices: pd.DataFrame, payments: pd.DataFrame) -> float:
    """Money received against invoices that are actually settled.

    Payments against an invoice still marked open are excluded on purpose: that
    money is a partial payment, already netted out of ``outstanding``. Counting it
    here too would report it twice and inflate the recovery rate.

    ``payments`` is a DataFrame with *no columns at all* when a scenario has none,
    so the emptiness guard has to come before any column access.
    """
    if payments.empty or invoices.empty:
        return 0.0
    settled = invoices[invoices["status"] == _SETTLED_STATUS]
    if settled.empty:
        return 0.0
    settled_payments = payments[payments["invoice_id"].isin(settled["id"])]
    return float(settled_payments["amount"].sum())


def _unscored_client_count(clients: pd.DataFrame, scores: list[Score]) -> int:
    """Clients in the scenario that carry no persisted score.

    Reported rather than folded into the totals (design D3). E4 excludes clients
    with nothing outstanding from scoring, so a denominator drawn from a different
    population than its numerator would make the expected recovery rate quietly
    wrong.
    """
    if clients.empty:
        return 0
    scored_ids = {str(score.client_id) for score in scores}
    return int((~clients["id"].astype(str).isin(scored_ids)).sum())
