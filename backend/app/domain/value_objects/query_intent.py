"""The constrained vocabulary a natural-language question is translated into (ADR-008).

**This module is the security boundary of the NL query feature.** The language
model never emits SQL and no string it returns reaches the database; what
crosses from the model into the application is a :class:`QueryIntent`, and a
``QueryIntent`` cannot hold a value that is not an enum member. Prompt injection
through the question box therefore cannot reach storage: the worst a hostile
question achieves is an intent the validator rejects, or a valid intent over the
caller's own already-authorised scenario.

The guarantee is structural rather than procedural. There is no allow-list
*check* to forget to call, because the field types are the allow-list.

Two conventions here are load-bearing and both encode defects this repository
has actually shipped:

* ``Dimension`` members take their values from ``portfolio_kpis``'s exported
  constants rather than re-typed literals. That module says why in its own
  docstring: a typo'd key would silently produce an empty breakdown.
* Filter values are validated against :class:`~app.domain.enums.ScoreCategory`
  members, never against capitalised strings. Comparing ``"High"`` to a
  lowercase ``StrEnum`` is the live ``/prioritized?category=High`` defect, and
  s5.1 shipped the same species in the ``days_overdue`` filter. Here it raises.

``avg_days_overdue`` is deliberately absent, and so is ADR-008's ``limit``. See
``work/epics/e6-executive-panel/stories/s6.3-design.md`` §D1: the three metrics
below are exactly the fields ``SegmentBucket`` carries, which is what makes
every metric computable for every dimension *by construction* instead of by
test. ``limit`` is unimplemented because no dimension produces more than four
buckets — there is nothing to limit.
"""

from enum import StrEnum
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ScoreCategory
from app.domain.value_objects.portfolio_kpis import (
    AMOUNT_RANGE,
    DAYS_OVERDUE_BUCKET,
    DAYS_OVERDUE_LABELS,
    SCORE_CATEGORY,
)


class Metric(StrEnum):
    """What is being measured.

    Exactly the three numeric fields of ``SegmentBucket``, so grouping any
    metric by any dimension is always answerable from the aggregate.
    """

    OUTSTANDING = "outstanding"
    EXPECTED_RECOVERABLE = "expected_recoverable"
    CLIENT_COUNT = "client_count"


class Dimension(StrEnum):
    """How the measurement is broken down.

    Values come from ``portfolio_kpis``'s module constants — the same keys the
    aggregate stores its segmentation under — so a rename there is a type error
    here rather than an empty result at runtime.
    """

    DAYS_OVERDUE_BUCKET = DAYS_OVERDUE_BUCKET
    AMOUNT_RANGE = AMOUNT_RANGE
    SCORE_CATEGORY = SCORE_CATEGORY


class Operator(StrEnum):
    """Comparison used by a filter.

    Equality only. Ranges and negation are not in E6's scope, and an operator
    the executor cannot honour would be a vocabulary that lies about itself.
    """

    EQ = "eq"


def _score_category_labels() -> list[str]:
    return [member.value for member in ScoreCategory]


#: Dimensions whose bucket labels form a closed set, and the labels themselves.
#:
#: ``amount_range`` is deliberately excluded: its labels are per-scenario
#: quartile strings (``"$0 – $2,812"``) computed from the portfolio's own
#: balance distribution, so there is nothing stable to allow-list against. It
#: remains fully supported as a ``group_by`` — only filtering is refused.
FILTERABLE_DIMENSIONS: Final[dict[str, list[str]]] = {
    SCORE_CATEGORY: _score_category_labels(),
    DAYS_OVERDUE_BUCKET: list(DAYS_OVERDUE_LABELS),
}

#: What the system can answer, rendered verbatim into the "cannot answer"
#: response so a refused director learns the vocabulary instead of guessing.
#:
#: Derived from the enums rather than hand-maintained: help text that drifts
#: from the validator is worse than no help text, because it invites questions
#: that will be rejected.
SUPPORTED_VOCABULARY: Final[dict[str, Any]] = {
    "metrics": [m.value for m in Metric],
    "dimensions": [d.value for d in Dimension],
    "filterable": FILTERABLE_DIMENSIONS,
}


class Filter(BaseModel):
    """One equality constraint on a segmentation dimension.

    Validation rejects both an unfilterable dimension and a value outside that
    dimension's closed label set. Rejecting is the point: a filter that matches
    nothing while looking well-formed is the failure mode that hid three
    defects in this codebase behind tests that iterated empty lists.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: Dimension
    operator: Operator = Operator.EQ
    value: str

    @model_validator(mode="after")
    def _value_must_be_in_the_dimension_vocabulary(self) -> "Filter":
        allowed = FILTERABLE_DIMENSIONS.get(self.dimension.value)
        if allowed is None:
            filterable = ", ".join(sorted(FILTERABLE_DIMENSIONS))
            raise ValueError(
                f"{self.dimension.value} cannot be filtered — its labels vary per scenario. "
                f"Filterable dimensions: {filterable}."
            )
        if self.value not in allowed:
            raise ValueError(
                f"{self.value!r} is not a value of {self.dimension.value}. "
                f"Expected one of: {', '.join(allowed)}."
            )
        return self


class QueryIntent(BaseModel):
    """A question, reduced to something the executor can answer safely.

    ``extra="forbid"`` is deliberate and not stylistic. A model that returns
    ``{"metric": "outstanding", "sql": "…"}`` must be **refused**; silently
    dropping the unknown key would mean accepting a response the system did not
    understand, which is precisely the situation ADR-008 exists to prevent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: Metric
    group_by: Dimension | None = None
    filters: list[Filter] = Field(default_factory=list, max_length=3)
