from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class ScenarioORM(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(50))
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="inactive")
    created_at: Mapped[datetime] = mapped_column()


class ClientORM(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    sector_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_history_pattern: Mapped[str] = mapped_column(String(50))
    #: Position of this client in its scenario's generation sequence.
    #:
    #: `id` is a random surrogate key assigned by persistence, so it carries no ordering
    #: information. OutcomeLabeller applies a *seeded* random draw along an axis ordered by
    #: this column — ordering it by `id` instead made the same seed produce a different
    #: model on every run (BUG-05, ADR-011).
    generation_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class InvoiceORM(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    folio: Mapped[str] = mapped_column(String(50))
    amount: Mapped[float] = mapped_column(Float)
    issue_date: Mapped[datetime] = mapped_column()
    due_date: Mapped[datetime] = mapped_column()
    days_overdue: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50))


class PaymentORM(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[datetime] = mapped_column()
    method: Mapped[str] = mapped_column(String(50))


class ScoreORM(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"))
    score_value: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(20))
    explanation: Mapped[str] = mapped_column(Text)
    scored_at: Mapped[datetime] = mapped_column()


class CommunicationORM(Base):
    __tablename__ = "communications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20))
    tone: Mapped[str] = mapped_column(String(20))
    draft_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column()
    # NFR-06 auditability (BUG-08). Nullable because rows written before this existed
    # genuinely do not know their provenance — backfilling a plausible value would
    # falsify the audit record, which is worse than recording that it is unknown.
    operator_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ContactResultORM(Base):
    __tablename__ = "contact_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    communication_id: Mapped[str | None] = mapped_column(
        ForeignKey("communications.id", ondelete="CASCADE"), nullable=True
    )
    result_type: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column()
