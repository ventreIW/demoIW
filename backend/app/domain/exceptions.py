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
