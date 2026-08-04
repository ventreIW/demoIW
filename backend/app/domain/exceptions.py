class EntityNotFoundError(Exception):
    def __init__(self, entity_type: str, entity_id: str) -> None:
        super().__init__(f"{entity_type} with id={entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


class InvalidOperationError(Exception):
    pass


class ExternalServiceError(Exception):
    """Raised when an external service (e.g., LLM API) returns an error."""

    pass


class PortfolioNotScoredError(Exception):
    """Raised when portfolio KPIs are requested for a scenario with no persisted scores.

    Deliberately an error rather than an empty aggregate (ADR-009): a portfolio of
    zero expected recoverable value is a legitimate answer for a fully settled book
    and an illegitimate one for an unscored book, and returning zeros makes the two
    indistinguishable to whoever is reading the dashboard.

    Lives here rather than in the router because the natural-language query executor
    (s6.3) is the second caller of the same aggregate and must be refused identically.
    """

    def __init__(self, scenario_id: str) -> None:
        super().__init__(
            f"Scenario {scenario_id} has no persisted scores. "
            f"POST /api/v1/scenarios/{scenario_id}/score first."
        )
        self.scenario_id = scenario_id


class InsufficientTrainingDataError(Exception):
    """Raised when a scenario cannot produce a usable training set.

    Deliberately loud: silently returning a single-class or near-empty training
    set would let s4.3 train a model that reports a plausible score while having
    learned nothing.
    """

    pass
