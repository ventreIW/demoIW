"""Answer a natural-language question about a scored portfolio (RF-06.3, RF-06.4).

Orchestrates the four stages of ADR-008 and owns **every** degradation path:

    load aggregate → translate → execute → narrate → cite

Order is load-bearing. The aggregate is fetched *first*, so an unscored
scenario is refused with a 409 before a single request is spent against the
free tier's 50/day cap. Translation comes before execution because execution
accepts a ``QueryIntent`` and nothing else. Narration comes last and sees only
computed numbers.

**Nothing here fabricates.** Three separate failures — an unsupported question,
an unreadable reply, an unavailable provider — converge on one response shape
so the frontend has one thing to render, while keeping distinct reasons so an
operator reading logs can tell them apart. None of them carries a figure.

The scenario citation is attached from the aggregate. The model is never asked
which portfolio it answered about, because a model that can be wrong about the
numbers can also be wrong about their source.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from app.application.services.nl_query_translator import (
    NlQueryTranslator,
    OutOfVocabularyError,
    TranslationFailedError,
)
from app.application.services.query_executor import QueryResult, execute
from app.config import settings
from app.domain.enums import Sector
from app.domain.exceptions import ExternalServiceError
from app.domain.value_objects.portfolio_kpis import PortfolioKpis
from app.domain.value_objects.query_intent import (
    SUPPORTED_VOCABULARY,
    Dimension,
    Metric,
    QueryIntent,
)
from app.ports.llm_port import ILLMPort

log = logging.getLogger(__name__)

#: Loads the portfolio aggregate for a scenario. Injected rather than imported
#: so the use case stays testable without repositories — the composition root
#: binds it to ``kpi_aggregate_service.fetch_portfolio_kpis``.
LoadKpis = Callable[[UUID], Awaitable[PortfolioKpis]]


class RefusalReason(StrEnum):
    """Why a question was not answered.

    One response shape, three distinguishable causes. The frontend can render a
    single "cannot answer" state while an operator reading logs still knows
    whether the vocabulary was too small or the provider was down.
    """

    OUT_OF_VOCABULARY = "out_of_vocabulary"
    TRANSLATION_FAILED = "translation_failed"
    TRANSLATION_UNAVAILABLE = "translation_unavailable"


@dataclass(frozen=True)
class NlAnswer:
    """The answer, or an honest account of why there isn't one.

    Citation fields are always populated, including on refusals: a director who
    is told "I cannot answer that" still needs to know which portfolio was not
    answered about.
    """

    answerable: bool
    question: str
    scenario_id: UUID
    scenario_name: str
    sector: Sector
    scored_at: datetime
    intent: QueryIntent | None = None
    result: QueryResult | None = None
    narrative: str | None = None
    reason: RefusalReason | None = None
    supported: dict[str, Any] | None = None


#: Spanish labels for the narrate prompt. The narrator writes for a Mexican
#: finance director, so it is handed domain language rather than enum values.
_METRIC_LABELS: dict[Metric, str] = {
    Metric.OUTSTANDING: "monto vencido",
    Metric.EXPECTED_RECOVERABLE: "recuperación esperada",
    Metric.CLIENT_COUNT: "número de clientes",
}

_DIMENSION_LABELS: dict[Dimension, str] = {
    Dimension.DAYS_OVERDUE_BUCKET: "antigüedad del atraso",
    Dimension.AMOUNT_RANGE: "rango de monto",
    Dimension.SCORE_CATEGORY: "categoría de score",
}


class AnswerNlQuery:
    """Question in, answer or refusal out. Never a fabricated number."""

    def __init__(
        self,
        translator: NlQueryTranslator,
        llm_port: ILLMPort,
        prompt_dir: Path | str,
        load_kpis: LoadKpis,
        model: str | None = None,
    ) -> None:
        self._translator = translator
        self._llm = llm_port
        self._prompt_dir = Path(prompt_dir)
        self._load_kpis = load_kpis
        self._model = model or settings.MODEL_NL_QUERY
        self._narrate_template = self._load_template()

    def _load_template(self) -> str:
        template_path = self._prompt_dir / "nl_query" / "v1_narrate.txt"
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"Prompt template not found at {template_path}")

    async def execute(self, scenario_id: UUID, question: str) -> NlAnswer:
        """Answer ``question`` about ``scenario_id``.

        Raises:
            EntityNotFoundError: the scenario does not exist.
            PortfolioNotScoredError: the scenario carries no persisted scores.
                Raised **before** any LLM request, so an unscorable question
                costs nothing against the daily cap.
        """
        kpis = await self._load_kpis(scenario_id)

        try:
            intent = await self._translator.translate(question)
        except OutOfVocabularyError:
            return self._refuse(question, kpis, RefusalReason.OUT_OF_VOCABULARY)
        except TranslationFailedError:
            return self._refuse(question, kpis, RefusalReason.TRANSLATION_FAILED)
        except ExternalServiceError:
            log.warning("nl_query_translation_unavailable", extra={"scenario": str(scenario_id)})
            return self._refuse(question, kpis, RefusalReason.TRANSLATION_UNAVAILABLE)

        result = execute(intent, kpis)
        narrative = await self._narrate(result, kpis)

        return NlAnswer(
            answerable=True,
            question=question,
            scenario_id=kpis.scenario_id,
            scenario_name=kpis.scenario_name,
            sector=kpis.sector,
            scored_at=kpis.scored_at,
            intent=intent,
            result=result,
            narrative=narrative,
        )

    def _refuse(self, question: str, kpis: PortfolioKpis, reason: RefusalReason) -> NlAnswer:
        """Build a refusal.

        One builder for all three paths so they cannot drift apart — and so the
        invariant "a refusal carries no figures" is enforced in one place
        rather than repeated at three call sites.
        """
        return NlAnswer(
            answerable=False,
            question=question,
            scenario_id=kpis.scenario_id,
            scenario_name=kpis.scenario_name,
            sector=kpis.sector,
            scored_at=kpis.scored_at,
            reason=reason,
            supported=SUPPORTED_VOCABULARY,
        )

    async def _narrate(self, result: QueryResult, kpis: PortfolioKpis) -> str | None:
        """Ask the model to describe ``result`` in Spanish.

        Receives the computed figures and the portfolio name — **never the
        question** (design D5). There is therefore no channel through which an
        instruction embedded in the question could reach the narrator.

        Returns ``None`` when narration fails. Losing the prose must not lose
        the answer: the figures are the deliverable and the paragraph is a
        convenience, so a director with a chart and no narrative is better
        served than one with an error page.
        """
        prompt = self._narrate_template.format(
            scenario_name=kpis.scenario_name,
            metric_label=_METRIC_LABELS[result.metric],
            group_by_label=(
                _DIMENSION_LABELS[result.group_by] if result.group_by else "sin desglose"
            ),
            total=f"{result.total:,.2f}",
            series="\n".join(f"- {p.label or 'total'}: {p.value:,.2f}" for p in result.series),
        )
        try:
            return await self._llm.generate(prompt, model=self._model, max_tokens=300)
        except ExternalServiceError:
            log.warning("nl_query_narration_unavailable")
            return None
