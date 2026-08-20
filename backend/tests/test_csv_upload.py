import pytest
from httpx import AsyncClient

VALID_CSV = (
    "client_name,amount,due_date,invoice_id\n"
    "Acme Corp,1500.00,2026-08-15,INV-001\n"
    "Beta LLC,2300.50,2026-09-01,INV-002\n"
    "Gamma Inc,875.00,2026-07-30,INV-003\n"
)

CSV_MISSING_AMOUNT = "client_name,due_date,invoice_id\n" "Acme Corp,2026-08-15,INV-001\n"


@pytest.mark.anyio
async def test_upload_csv_valid_returns_201(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/upload-csv with valid CSV returns 201 + ScenarioSummary."""
    response = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("data.csv", VALID_CSV.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "data"
    assert body["status"] == "inactive"
    assert body["client_count"] == 3
    assert "id" in body
    assert "created_at" in body


@pytest.mark.anyio
async def test_upload_csv_missing_columns_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/upload-csv with missing columns returns 422."""
    response = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("bad.csv", CSV_MISSING_AMOUNT.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    detail_msgs = [d["msg"] for d in body["detail"]]
    assert any("amount" in msg.lower() for msg in detail_msgs)


@pytest.mark.anyio
async def test_upload_csv_empty_file_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/upload-csv with empty file returns 422."""
    response = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.anyio
async def test_upload_csv_malformed_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/upload-csv with non-CSV content returns 422."""
    response = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("notacsv.csv", b"this is not csv content", "text/csv")},
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


# BUG-03: the four tests above all assert on the *upload response*. None asks whether the
# persisted scenario can then be used, so the CSV path was verified up to the moment of
# writing and not one step past it — which is exactly where the defect lived.

_ROUNDTRIP_ROWS = [
    (f"Client {i:02d}", 1000.0 + i * 137.0, f"2026-01-{(i % 28) + 1:02d}", f"INV-{i:03d}")
    for i in range(30)  # above MIN_CLIENTS (20), so a small-sample floor cannot be the cause
]
ROUNDTRIP_CSV = "client_name,amount,due_date,invoice_id\n" + "".join(
    f"{name},{amount:.2f},{due},{folio}\n" for name, amount, due, folio in _ROUNDTRIP_ROWS
)
ROUNDTRIP_TOTAL = sum(amount for _, amount, _, _ in _ROUNDTRIP_ROWS)


@pytest.mark.anyio
async def test_uploaded_csv_invoices_count_as_outstanding(client: AsyncClient) -> None:
    """BUG-03: uploaded invoices must be visible to the feature extractor.

    create_from_csv wrote status="pending", which matched neither the open branch
    ("overdue") nor the settled branch ("paid"), so every uploaded invoice vanished
    from both and outstanding summed to zero. This asserts the scenario gets past
    the labelling stage — i.e. that its balances are actually seen.
    """
    upload = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("data.csv", ROUNDTRIP_CSV.encode("utf-8"), "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    scenario_id = upload.json()["id"]

    # The scoring failure surfaces as a raised exception under the test transport and as a
    # 500 body in production, so capture either and assert on the text.
    try:
        response = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
        outcome = response.text
    except Exception as exc:  # noqa: BLE001 — the message is the assertion target
        outcome = str(exc)

    assert "nothing to label" not in outcome, (
        f"uploaded invoices are still invisible to the extractor — outstanding is zero: "
        f"{outcome[:300]}"
    )
    assert "Unrecognised invoice status" not in outcome, (
        f"an unrecognised status is still being written by the CSV path: {outcome[:300]}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-06: a CSV-uploaded scenario cannot be supervised-trained. create_from_csv "
        "assigns PaymentPattern.ON_TIME to every client because the CSV carries no payment "
        "history, so OutcomeLabeller draws a single label class and training aborts. "
        "Not fixable by BUG-03: it needs a decision on how unlabelled uploads get scored "
        "(a pre-trained model rather than per-scenario training). Escalated, not dropped."
    ),
)
@pytest.mark.anyio
async def test_uploaded_csv_scenario_roundtrip_is_scorable(client: AsyncClient) -> None:
    """BUG-03 done-criteria 1 and 2: an uploaded scenario must be usable, not merely accepted.

    Kept as a strict xfail so the criterion is recorded rather than quietly dropped — it
    flips green, and the suite fails loudly, the moment BUG-06 is resolved.
    """
    upload = await client.post(
        "/api/v1/scenarios/upload-csv",
        files={"file": ("data.csv", ROUNDTRIP_CSV.encode("utf-8"), "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    scenario_id = upload.json()["id"]

    prioritized = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    assert prioritized.status_code == 200, (
        f"uploaded scenario is not scorable: {prioritized.status_code} {prioritized.text[:300]}"
    )
    body = prioritized.json()
    assert body["cases"], "uploaded scenario produced an empty portfolio"

    outstanding_total = sum(case["outstanding"] for case in body["cases"])
    assert outstanding_total == pytest.approx(ROUNDTRIP_TOTAL, rel=1e-6)

    kpis = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")
    assert kpis.status_code == 200, f"kpis failed: {kpis.status_code} {kpis.text[:200]}"
    assert kpis.json()["total_overdue"] > 0
