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
