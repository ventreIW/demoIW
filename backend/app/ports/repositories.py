from abc import ABC, abstractmethod
from uuid import UUID

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
