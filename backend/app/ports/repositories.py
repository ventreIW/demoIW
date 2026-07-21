from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.client import Client
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.scenario import Scenario


class IScenarioRepository(ABC):
    """Abstract port for scenario persistence operations."""

    @abstractmethod
    async def list_all(self) -> list[Scenario]:
        """Return all scenarios ordered by created_at desc."""
        ...

    @abstractmethod
    async def get_by_id(self, scenario_id: UUID) -> Scenario | None:
        """Return a single scenario by ID, or None if not found."""
        ...

    @abstractmethod
    async def add(self, scenario: Scenario) -> Scenario:
        """Persist a new scenario and return it with assigned ID."""
        ...

    @abstractmethod
    async def set_active(self, scenario_id: UUID) -> Scenario:
        """Set the given scenario as active, deactivating any currently active one."""
        ...

    @abstractmethod
    async def get_active(self) -> Scenario | None:
        """Return the currently active scenario, or None."""
        ...

    @abstractmethod
    async def get_client_count(self, scenario_id: UUID) -> int:
        """Return the number of clients associated with a scenario."""
        ...

    @abstractmethod
    async def create_from_csv(self, scenario: Scenario, rows: list[dict[str, str]]) -> Scenario:
        """Create a scenario with clients and invoices from parsed CSV rows."""
        ...


class IClientRepository(ABC):
    """Abstract port for client persistence operations."""

    @abstractmethod
    async def add(self, client: Client) -> Client:
        """Persist a new client and return it with assigned ID."""
        ...

    @abstractmethod
    async def add_many(self, clients: list[Client]) -> list[Client]:
        """Persist multiple new clients and return them with assigned IDs."""
        ...

    @abstractmethod
    async def get_by_scenario_id(self, scenario_id: UUID) -> list[Client]:
        """Return all clients associated with a scenario."""
        ...

    @abstractmethod
    async def get_by_id(self, client_id: UUID) -> Client | None:
        """Return a single client by ID, or None if not found."""
        ...


class IInvoiceRepository(ABC):
    """Abstract port for invoice persistence operations."""

    @abstractmethod
    async def add(self, invoice: Invoice) -> Invoice:
        """Persist a new invoice and return it with assigned ID."""
        ...

    @abstractmethod
    async def add_many(self, invoices: list[Invoice]) -> list[Invoice]:
        """Persist multiple new invoices and return them with assigned IDs."""
        ...

    @abstractmethod
    async def get_by_scenario_id(self, scenario_id: UUID) -> list[Invoice]:
        """Return all invoices associated with a scenario."""
        ...

    @abstractmethod
    async def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Return a single invoice by ID, or None if not found."""
        ...


class IPaymentRepository(ABC):
    """Abstract port for payment persistence operations."""

    @abstractmethod
    async def add(self, payment: Payment) -> Payment:
        """Persist a new payment and return it with assigned ID."""
        ...

    @abstractmethod
    async def add_many(self, payments: list[Payment]) -> list[Payment]:
        """Persist multiple new payments and return them with assigned IDs."""
        ...

    @abstractmethod
    async def get_by_scenario_id(self, scenario_id: UUID) -> list[Payment]:
        """Return all payments associated with a scenario."""
        ...

    @abstractmethod
    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        """Return a single payment by ID, or None if not found."""
        ...
