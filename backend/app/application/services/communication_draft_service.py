from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.domain.enums import Channel, Tone
from app.ports.llm_port import ILLMPort

if TYPE_CHECKING:
    from app.routers.cases import CaseDetailResponse

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaseDetail:
    """Minimal case detail for prompt building — decoupled from router response model."""

    client_name: str
    sector_description: str | None
    payment_history_pattern: str
    invoices: list[dict[str, str | int | float]]
    payments: list[dict[str, str | int | float]]
    score_value: float | None
    score_category: str | None
    communications: list[dict[str, str]]


class CommunicationDraftService:
    """Service for generating communication drafts via LLM."""

    def __init__(
        self,
        llm_port: ILLMPort,
        prompt_dir: Path | str,
        model: str | None = None,
    ) -> None:
        self._llm = llm_port
        self._prompt_dir = Path(prompt_dir)
        self._model = model or settings.MODEL_COMMUNICATIONS
        self._template = self._load_template()

    def _load_template(self) -> str:
        template_path = self._prompt_dir / "communications" / "v1_draft.txt"
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"Prompt template not found at {template_path}")

    def _build_prompt(
        self,
        case_detail: CaseDetail,
        channel: Channel,
        tone: Tone,
    ) -> str:
        """Build the prompt by filling all placeholders from case detail."""
        invoice_lines = [
            f"- {inv['folio']}: {inv['amount']} "
            f"(due {inv['due_date']}, {inv['days_overdue']} days overdue, status: {inv['status']})"
            for inv in case_detail.invoices
        ]
        invoice_list = "\n".join(invoice_lines) if invoice_lines else "No outstanding invoices."

        payment_lines = [
            f"- {pmt['amount']} on {pmt['payment_date']} via {pmt['method']}"
            for pmt in case_detail.payments
        ]
        payment_history = "\n".join(payment_lines) if payment_lines else "No payment history."

        comm_lines = [
            f"- {c['channel']} ({c['tone']}): {c['draft_text'][:100]}... "
            f"(status: {c['status']}, {c['created_at']})"
            for c in case_detail.communications
        ]
        comms_log = "\n".join(comm_lines) if comm_lines else "No previous communications."

        return self._template.format(
            client_name=case_detail.client_name,
            sector_description=case_detail.sector_description or "N/A",
            payment_history_pattern=case_detail.payment_history_pattern,
            invoice_list=invoice_list,
            payment_history=payment_history,
            score_value=case_detail.score_value if case_detail.score_value is not None else "N/A",
            score_category=case_detail.score_category or "N/A",
            comms_log=comms_log,
            channel=channel.value,
            tone=tone.value,
        )

    async def generate(
        self,
        case_detail: CaseDetail,
        channel: Channel,
        tone: Tone,
    ) -> str:
        """Generate a communication draft using the LLM."""
        prompt = self._build_prompt(case_detail, channel, tone)
        log.info(
            "Generating communication draft",
            extra={"channel": channel.value, "tone": tone.value},
        )
        return await self._llm.generate(prompt, model=self._model, max_tokens=512)


def case_detail_response_to_domain(response: CaseDetailResponse) -> CaseDetail:
    """Convert router CaseDetailResponse to internal CaseDetail for prompt building."""
    return CaseDetail(
        client_name=response.client.name,
        sector_description=response.client.sector_description,
        payment_history_pattern=response.client.payment_history_pattern,
        invoices=[
            {
                "folio": inv.folio,
                "amount": inv.amount,
                "due_date": inv.due_date,
                "days_overdue": inv.days_overdue,
                "status": inv.status,
            }
            for inv in response.invoices
        ],
        payments=[
            {
                "amount": pmt.amount,
                "payment_date": pmt.payment_date,
                "method": pmt.method,
            }
            for pmt in response.payments
        ],
        score_value=response.score.score_value if response.score else None,
        score_category=response.score.category if response.score else None,
        communications=[
            {
                "channel": c.channel,
                "tone": c.tone,
                "draft_text": c.draft_text,
                "status": c.status,
                "created_at": c.created_at,
            }
            for c in response.communications
        ],
    )
