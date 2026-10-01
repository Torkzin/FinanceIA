from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import get_current_user
from app.api.v1.routes import integrations
from app.db.models import User
from app.db.session import get_session
from app.main import app
from app.schemas.erp import ERPSyncCounts, ERPSyncResponse


def user_with_role(role: str) -> User:
    return User(
        id=uuid4(),
        company_id=uuid4(),
        full_name="Test User",
        email=f"{role}@test.demo",
        password_hash="not-used-by-contract-tests",
        role=role,
        is_active=True,
    )


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def override_dependencies(user: User) -> None:
    async def current_user_override() -> User:
        return user

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = current_user_override
    app.dependency_overrides[get_session] = session_override


@pytest.mark.asyncio
async def test_external_erp_contract_is_public_and_valid(client: AsyncClient) -> None:
    vendors = await client.get("/external-api/vendors")
    invoices = await client.get("/external-api/invoices")

    assert vendors.status_code == 200
    assert invoices.status_code == 200
    assert len(vendors.json()) == 4
    assert len(invoices.json()) == 5
    assert {"external_id", "document_number", "name"} <= vendors.json()[0].keys()
    assert {"external_id", "vendor_external_id", "amount"} <= invoices.json()[0].keys()


@pytest.mark.asyncio
async def test_erp_sync_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/v1/integrations/erp/sync")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_manager_cannot_execute_erp_sync(client: AsyncClient) -> None:
    override_dependencies(user_with_role("manager"))

    response = await client.post("/api/v1/integrations/erp/sync")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_finance_role_receives_typed_erp_result(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    finance_user = user_with_role("finance")
    override_dependencies(finance_user)
    completed_at = datetime.now(UTC)

    async def fake_sync(*_args, **_kwargs) -> ERPSyncResponse:
        return ERPSyncResponse(
            run_id=uuid4(),
            source="contract-test",
            checkpoint="contract-test:1",
            vendors=ERPSyncCounts(received=1, created=1),
            invoices=ERPSyncCounts(received=1, created=1),
            warnings=[],
            completed_at=completed_at,
        )

    monkeypatch.setattr(integrations, "sync_erp", fake_sync)
    response = await client.post("/api/v1/integrations/erp/sync")

    assert response.status_code == 200
    assert response.json()["source"] == "contract-test"
    assert response.json()["vendors"]["created"] == 1


@pytest.mark.asyncio
async def test_manager_cannot_create_supplier(client: AsyncClient) -> None:
    override_dependencies(user_with_role("manager"))

    response = await client.post(
        "/api/v1/suppliers",
        json={"name": "Protected Supplier", "document_number": "DOC-1234"},
    )

    assert response.status_code == 403
