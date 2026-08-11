"""The vocabulary boundary for natural-language queries (s6.3 T1, ADR-008).

This module is the story's security property. Everything downstream is safe
*because* a ``QueryIntent`` cannot hold a string that is not an enum member —
so these tests are not input validation trivia, they are the guarantee.

Two of them encode defects this codebase has actually shipped:

* :func:`test_score_category_filter_rejects_capitalised_value` — the live
  ``/prioritized?category=High`` bug, where the router compares against
  ``{"High","Medium","Low"}`` while ``ScoreCategory`` values are lowercase, so
  the filter matches nothing for every input the router accepts. s5.1 shipped
  the same species in the ``days_overdue`` filter. Rejecting loudly at
  validation is the only outcome that cannot fail silently.
* :func:`test_extra_keys_are_rejected` — a model that returns
  ``{"metric": "outstanding", "sql": "..."}`` must be **refused**, not quietly
  accepted with the extra key dropped.
"""

import pytest
from pydantic import ValidationError

from app.domain.enums import ScoreCategory
from app.domain.value_objects.portfolio_kpis import (
    AMOUNT_RANGE,
    DAYS_OVERDUE_BUCKET,
    SCORE_CATEGORY,
)
from app.domain.value_objects.query_intent import (
    SUPPORTED_VOCABULARY,
    Dimension,
    Filter,
    Metric,
    Operator,
    QueryIntent,
)


class TestVocabulary:
    """The enums must mirror what the s6.1 aggregate actually exposes."""

    def test_dimension_values_are_the_aggregate_segmentation_keys(self) -> None:
        """Built from ``portfolio_kpis``'s constants, never re-typed literals.

        ``portfolio_kpis.py`` exports these three names *for this purpose*: a
        typo'd key here would produce an empty breakdown that no other test
        notices, because every dimension lookup would simply miss.
        """
        assert {d.value for d in Dimension} == {
            DAYS_OVERDUE_BUCKET,
            AMOUNT_RANGE,
            SCORE_CATEGORY,
        }

    def test_metrics_are_exactly_the_fields_a_segment_bucket_carries(self) -> None:
        """Three metrics, not ADR-008's four (design D1).

        ``SegmentBucket`` carries ``client_count``, ``outstanding`` and
        ``expected_recoverable``. ``avg_days_overdue`` has no home in the
        aggregate, so including it would create cells with no data source.
        """
        assert {m.value for m in Metric} == {
            "outstanding",
            "expected_recoverable",
            "client_count",
        }

    def test_supported_vocabulary_is_derived_not_hand_maintained(self) -> None:
        """The refusal response renders this; drift would make the help lie."""
        assert SUPPORTED_VOCABULARY["metrics"] == [m.value for m in Metric]
        assert SUPPORTED_VOCABULARY["dimensions"] == [d.value for d in Dimension]
        assert set(SUPPORTED_VOCABULARY["filterable"]) == {SCORE_CATEGORY, DAYS_OVERDUE_BUCKET}
        assert SUPPORTED_VOCABULARY["filterable"][SCORE_CATEGORY] == ["high", "medium", "low"]


class TestFilterValidation:
    def test_score_category_filter_accepts_enum_value(self) -> None:
        f = Filter(dimension=Dimension.SCORE_CATEGORY, operator=Operator.EQ, value="high")
        assert f.value == ScoreCategory.HIGH.value

    def test_score_category_filter_rejects_capitalised_value(self) -> None:
        """The live ``?category=High`` defect, refused instead of reproduced.

        Capitalised literals compared against a lowercase ``StrEnum`` is how
        ``/prioritized`` returns an empty portfolio for every valid input. Here
        it must raise, because a filter that matches nothing while looking
        correct is worse than one that fails.
        """
        with pytest.raises(ValidationError) as exc:
            Filter(dimension=Dimension.SCORE_CATEGORY, operator=Operator.EQ, value="High")
        assert "high" in str(exc.value)

    def test_days_overdue_filter_accepts_a_real_bucket_label(self) -> None:
        f = Filter(dimension=Dimension.DAYS_OVERDUE_BUCKET, operator=Operator.EQ, value="31-60")
        assert f.value == "31-60"

    def test_days_overdue_filter_rejects_an_invented_label(self) -> None:
        with pytest.raises(ValidationError):
            Filter(dimension=Dimension.DAYS_OVERDUE_BUCKET, operator=Operator.EQ, value="45-50")

    def test_amount_range_is_not_filterable(self) -> None:
        """Its labels are per-scenario quartile strings (``"$0 – $2,812"``).

        There is no closed set to allow-list against, so filtering on it is
        rejected rather than matched loosely against runtime text.
        """
        with pytest.raises(ValidationError) as exc:
            Filter(dimension=Dimension.AMOUNT_RANGE, operator=Operator.EQ, value="$0 – $2,812")
        message = str(exc.value)
        assert SCORE_CATEGORY in message and DAYS_OVERDUE_BUCKET in message

    def test_filter_is_frozen(self) -> None:
        f = Filter(dimension=Dimension.SCORE_CATEGORY, value="low")
        with pytest.raises(ValidationError):
            f.value = "high"  # type: ignore[misc]


class TestQueryIntentValidation:
    def test_minimal_intent_is_ungrouped_and_unfiltered(self) -> None:
        intent = QueryIntent(metric=Metric.OUTSTANDING)
        assert intent.group_by is None
        assert intent.filters == []

    def test_intent_accepts_group_by_and_filters(self) -> None:
        intent = QueryIntent(
            metric=Metric.EXPECTED_RECOVERABLE,
            group_by=Dimension.SCORE_CATEGORY,
            filters=[Filter(dimension=Dimension.SCORE_CATEGORY, value="high")],
        )
        assert intent.metric is Metric.EXPECTED_RECOVERABLE
        assert intent.group_by is Dimension.SCORE_CATEGORY
        assert len(intent.filters) == 1

    def test_unknown_metric_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QueryIntent(metric="avg_days_overdue")  # type: ignore[arg-type]

    def test_extra_keys_are_rejected(self) -> None:
        """``extra="forbid"`` is load-bearing, not stylistic.

        A model returning an ``sql`` key alongside a valid metric must be
        refused outright. Silently dropping the key would mean the system
        accepted a response it did not understand.
        """
        with pytest.raises(ValidationError):
            QueryIntent.model_validate({"metric": "outstanding", "sql": "DROP TABLE clients"})

    def test_filters_are_bounded(self) -> None:
        with pytest.raises(ValidationError):
            QueryIntent.model_validate(
                {
                    "metric": "outstanding",
                    "filters": [
                        {"dimension": SCORE_CATEGORY, "value": v}
                        for v in ("high", "medium", "low", "high")
                    ],
                }
            )

    def test_intent_is_frozen(self) -> None:
        intent = QueryIntent(metric=Metric.CLIENT_COUNT)
        with pytest.raises(ValidationError):
            intent.metric = Metric.OUTSTANDING  # type: ignore[misc]

    @pytest.mark.parametrize(
        "hostile",
        [
            {"metric": "outstanding; DROP TABLE clients"},
            {"metric": "outstanding", "group_by": "'; DELETE FROM scores --"},
            {"metric": "../../etc/passwd"},
            {"metric": "outstanding", "filters": [{"dimension": "clients", "value": "x"}]},
        ],
    )
    def test_hostile_payloads_cannot_construct_an_intent(self, hostile: dict) -> None:
        """No hostile string survives the boundary — this is ADR-008's claim.

        The worst a malicious translation achieves is a rejected intent. There
        is no code path that accepts an unrecognised field name, because the
        field names are enum members rather than strings.
        """
        with pytest.raises(ValidationError):
            QueryIntent.model_validate(hostile)
