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


class InsufficientTrainingDataError(Exception):
    """Raised when a scenario cannot produce a usable training set.

    Deliberately loud: silently returning a single-class or near-empty training
    set would let s4.3 train a model that reports a plausible score while having
    learned nothing.
    """

    pass
