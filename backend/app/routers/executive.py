"""Executive panel API — portfolio KPIs for the finance director (RF-06.1–06.2).

A thin adapter: it serialises the aggregate and does no arithmetic of its own.
Every figure is derived in the domain layer, so the dashboard cannot disagree
with the natural-language query layer that reads the same aggregate (ADR-008).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.application.services.kpi_aggregate_service import fetch_portfolio_kpis
from app.container import get_scenario_repo, get_score_repo
from app.domain.enums import Sector
from app.domain.exceptions import EntityNotFoundError, PortfolioNotScoredError
from app.domain.value_objects.portfolio_kpis import PortfolioKpis
from app.ports.repositories import IScenarioRepository, IScoreRepository

router = APIRouter(prefix="/api/v1/scenarios", tags=["executive"])


class ScenarioCitation(BaseModel):
    """Which dataset the figures came from (RF-06.4).

    Present on the KPI response as well as the NL answer so a director reading a
    number can always name its source.
    """

    id: UUID
    name: str
    sector: Sector


class SegmentBucketResponse(BaseModel):
    """One bar of one segmentation dimension.

    Bucket ``client_count`` sums to the response's ``client_count`` for every
    dimension — no client falls outside a bucket.
    """

    label: str
    client_count: int
    outstanding: float
    expected_recoverable: float


class PortfolioKpisResponse(BaseModel):
    """Response model matching the ``PortfolioKpis`` domain object exactly.

    Money definitions, so the numbers are defensible when someone asks:

    * ``total_outstanding`` — open invoices net of partial payments, over scored
      clients only.
    * ``total_expected_recoverable`` — sum of ``outstanding × score / 100``, in
      pesos rather than an index, because s4.3 kept ``predict_proba`` calibrated.
    * ``collected_to_date`` — payments against invoices that are actually settled.
      Partial payments are excluded here; they are already netted out of
      ``total_outstanding``, and counting them twice would inflate the recovery rate.
    * ``recovery_rate_actual`` — share of the whole book already settled. Historical:
      it does not move when a collector records a contact result.
    * ``recovery_rate_expected`` — share of the *unsettled remainder* the model
      expects to recover. Not a before/after pair with the previous figure; the two
      have different denominators, which is why neither is called "recovery rate"
      alone.
    * ``scored_at`` — when the persisted scoring run happened. ``/prioritized`` still
      re-fits per request (ADR-009), so surfacing this is what makes a stale
      dashboard legible instead of silently inconsistent with the operator queue.
    """

    scenario: ScenarioCitation
    scored_at: str
    client_count: int
    unscored_client_count: int
    total_outstanding: float
    total_expected_recoverable: float
    collected_to_date: float
    recovery_rate_actual: float
    recovery_rate_expected: float
    cases_by_category: dict[str, int]
    segmentation: dict[str, list[SegmentBucketResponse]]


@router.get("/{scenario_id}/kpis", response_model=PortfolioKpisResponse)
async def get_portfolio_kpis(
    scenario_id: UUID,
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    score_repo: IScoreRepository = Depends(get_score_repo),
) -> PortfolioKpisResponse:
    """Return portfolio-level KPIs and segmentation for a scored scenario.

    Reads persisted scores; it never fits a model (ADR-009). A scenario that has
    not been scored yields **409**, not a dashboard of zeros — score it first with
    ``POST /api/v1/scenarios/{scenario_id}/score``.
    """
    try:
        kpis = await fetch_portfolio_kpis(scenario_id, scenario_repo, score_repo)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario with id={scenario_id} not found")
    except PortfolioNotScoredError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return _to_response(kpis)


def _to_response(kpis: PortfolioKpis) -> PortfolioKpisResponse:
    return PortfolioKpisResponse(
        scenario=ScenarioCitation(id=kpis.scenario_id, name=kpis.scenario_name, sector=kpis.sector),
        scored_at=kpis.scored_at.isoformat(),
        client_count=kpis.client_count,
        unscored_client_count=kpis.unscored_client_count,
        total_outstanding=kpis.total_outstanding,
        total_expected_recoverable=kpis.total_expected_recoverable,
        collected_to_date=kpis.collected_to_date,
        recovery_rate_actual=kpis.recovery_rate_actual,
        recovery_rate_expected=kpis.recovery_rate_expected,
        # Keyed by the enum's *value* — lowercase. The capitalised-literal
        # comparison is the live ?category=High defect on /prioritized, where the
        # filter matches nothing for every input the router accepts.
        cases_by_category={
            category.value: count for category, count in kpis.cases_by_category.items()
        },
        segmentation={
            dimension: [
                SegmentBucketResponse(
                    label=bucket.label,
                    client_count=bucket.client_count,
                    outstanding=bucket.outstanding,
                    expected_recoverable=bucket.expected_recoverable,
                )
                for bucket in buckets
            ]
            for dimension, buckets in kpis.segmentation.items()
        },
    )
