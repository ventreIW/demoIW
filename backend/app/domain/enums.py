from enum import StrEnum


class Sector(StrEnum):
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    PROFESSIONAL_SERVICES = "professional_services"


class ScenarioStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PaymentPattern(StrEnum):
    ON_TIME = "on_time"
    DELAYED_30 = "delayed_30"
    DELAYED_60 = "delayed_60"
    DELAYED_90_PLUS = "delayed_90_plus"
    PARTIAL = "partial"
    DEFAULT = "default"


class InvoiceStatus(StrEnum):
    """Lifecycle state of an invoice.

    Values are the ones already persisted, so introducing this enum needs no migration.
    Before it existed, three producers and two consumers each spelled these as their own
    string literal and the CSV path invented a third word, ``"pending"``, which matched
    neither branch of the feature extractor and made uploaded scenarios unscorable (BUG-03).
    """

    OVERDUE = "overdue"
    PAID = "paid"


class ScoreCategory(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Channel(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"


class Tone(StrEnum):
    FORMAL = "formal"
    FIRM = "firm"
    URGENT = "urgent"


class CommunicationStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"


class ContactResultType(StrEnum):
    PROMISE_TO_PAY = "promise_to_pay"
    PARTIAL_PAYMENT = "partial_payment"
    NO_ANSWER = "no_answer"
    DISPUTED = "disputed"
    PAID = "paid"
