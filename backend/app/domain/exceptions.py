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

    #: Scenario.source value written by the CSV upload path.
    CSV_UPLOAD_SOURCE = "csv_upload"

    def __init__(self, scenario_id: str, scenario_source: str | None = None) -> None:
        if scenario_source == self.CSV_UPLOAD_SOURCE:
            # Telling the caller to POST /score would be advice that cannot work: an
            # uploaded CSV carries no payment history, so every client is assigned the
            # same payment pattern, the outcome labeller draws a single label class and
            # training aborts. Saying "score it first" would send them in a circle
            # (BUG-06, ADR-012).
            message = (
                f"Scenario {scenario_id} was created from a CSV upload and cannot be "
                f"scored. Scoring is trained per scenario on simulated collection "
                f"outcomes, which require the payment history a generated scenario has "
                f"and an uploaded file does not (ADR-006). Uploaded portfolios can be "
                f"listed, browsed and totalled, but not prioritised or scored. Use a "
                f"generated scenario for the intelligence features."
            )
        else:
            message = (
                f"Scenario {scenario_id} has no persisted scores. "
                f"POST /api/v1/scenarios/{scenario_id}/score first."
            )
        super().__init__(message)
        self.scenario_id = scenario_id
        self.scenario_source = scenario_source


class InsufficientTrainingDataError(Exception):
    """Raised when a scenario cannot produce a usable training set.

    Deliberately loud: silently returning a single-class or near-empty training
    set would let s4.3 train a model that reports a plausible score while having
    learned nothing.
    """

    pass
