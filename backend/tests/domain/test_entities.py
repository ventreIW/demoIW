from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.entities.client import Client
from app.domain.entities.communication import Communication
from app.domain.entities.contact_result import ContactResult
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.scenario import Scenario
from app.domain.entities.score import Score
from app.domain.enums import (
    Channel,
    CommunicationStatus,
    ContactResultType,
    PaymentPattern,
    ScenarioStatus,
    ScoreCategory,
    Sector,
    Tone,
)

# --- Enum tests ---


def test_sector_valid_values() -> None:
    assert Sector("manufacturing") == Sector.MANUFACTURING
    assert Sector("retail") == Sector.RETAIL
    assert Sector("professional_services") == Sector.PROFESSIONAL_SERVICES


def test_sector_invalid_raises() -> None:
    with pytest.raises(ValueError):
        Sector("unknown")


def test_scenario_status_values() -> None:
    assert ScenarioStatus("active") == ScenarioStatus.ACTIVE
    assert ScenarioStatus("inactive") == ScenarioStatus.INACTIVE


def test_payment_pattern_values() -> None:
    assert PaymentPattern("on_time") == PaymentPattern.ON_TIME
    assert PaymentPattern("delayed_90_plus") == PaymentPattern.DELAYED_90_PLUS


def test_score_category_values() -> None:
    assert ScoreCategory("high") == ScoreCategory.HIGH


def test_channel_values() -> None:
    assert Channel("email") == Channel.EMAIL
    assert Channel("whatsapp") == Channel.WHATSAPP


def test_tone_values() -> None:
    assert Tone("formal") == Tone.FORMAL
    assert Tone("urgent") == Tone.URGENT


def test_communication_status_values() -> None:
    assert CommunicationStatus("draft") == CommunicationStatus.DRAFT
    assert CommunicationStatus("sent") == CommunicationStatus.SENT


def test_contact_result_type_values() -> None:
    assert ContactResultType("promise_to_pay") == ContactResultType.PROMISE_TO_PAY
    assert ContactResultType("paid") == ContactResultType.PAID


# --- Entity tests ---


def test_scenario_is_frozen() -> None:
    s = Scenario(
        id=uuid4(),
        name="Test",
        sector=Sector.MANUFACTURING,
        seed=None,
        parameters={},
        source="generated",
        status=ScenarioStatus.INACTIVE,
        created_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        s.name = "mutated"  # type: ignore[misc]


def test_scenario_invalid_sector_raises() -> None:
    with pytest.raises(ValidationError):
        Scenario(
            id=uuid4(),
            name="X",
            sector="bad_sector",  # type: ignore[arg-type]
            seed=None,
            parameters={},
            source="generated",
            status=ScenarioStatus.INACTIVE,
            created_at=datetime.now(UTC),
        )


def test_client_is_frozen() -> None:
    c = Client(
        id=uuid4(),
        scenario_id=uuid4(),
        name="ACME",
        sector_description=None,
        payment_history_pattern=PaymentPattern.ON_TIME,
    )
    with pytest.raises(ValidationError):
        c.name = "mutated"  # type: ignore[misc]


def test_invoice_is_frozen() -> None:
    inv = Invoice(
        id=uuid4(),
        client_id=uuid4(),
        folio="F-001",
        amount=10000.0,
        issue_date=datetime.now(UTC),
        due_date=datetime.now(UTC),
        days_overdue=0,
        status="pending",
    )
    with pytest.raises(ValidationError):
        inv.folio = "mutated"  # type: ignore[misc]


def test_payment_is_frozen() -> None:
    p = Payment(
        id=uuid4(),
        invoice_id=uuid4(),
        amount=5000.0,
        payment_date=datetime.now(UTC),
        method="transfer",
    )
    with pytest.raises(ValidationError):
        p.amount = 0.0  # type: ignore[misc]


def test_score_is_frozen() -> None:
    sc = Score(
        id=uuid4(),
        client_id=uuid4(),
        scenario_id=uuid4(),
        score_value=0.75,
        category=ScoreCategory.HIGH,
        explanation="High payer",
        scored_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        sc.score_value = 0.0  # type: ignore[misc]


def test_communication_is_frozen() -> None:
    comm = Communication(
        id=uuid4(),
        client_id=uuid4(),
        scenario_id=uuid4(),
        channel=Channel.EMAIL,
        tone=Tone.FORMAL,
        draft_text="Dear client...",
        status=CommunicationStatus.DRAFT,
        created_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        comm.draft_text = "mutated"  # type: ignore[misc]


def test_contact_result_is_frozen() -> None:
    cr = ContactResult(
        id=uuid4(),
        client_id=uuid4(),
        communication_id=uuid4(),
        result_type=ContactResultType.PROMISE_TO_PAY,
        notes=None,
        recorded_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        cr.notes = "mutated"  # type: ignore[misc]
