import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Company,
    CostCenter,
    IntegrationConnection,
    IntegrationSyncRun,
    Invoice,
    Supplier,
)
from app.db.session import engine
from app.integrations.erp import MockERPAdapter
from app.services.erp_sync import sync_erp

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="set RUN_DB_TESTS=1 against a migrated disposable database",
    ),
]


@pytest_asyncio.fixture
async def db_session():
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest.mark.asyncio
async def test_erp_sync_is_idempotent_and_audited(db_session: AsyncSession) -> None:
    company = Company(id=uuid4(), name="ERP Test Company", slug=f"erp-test-{uuid4().hex}")
    db_session.add(company)
    db_session.add_all(
        [
            CostCenter(
                company_id=company.id,
                code="TEC",
                name="Technology",
                description="Test technology costs",
            ),
            CostCenter(
                company_id=company.id,
                code="OPS",
                name="Operations",
                description="Test operating costs",
            ),
        ]
    )
    await db_session.commit()

    first = await sync_erp(db_session, company.id, MockERPAdapter())
    second = await sync_erp(db_session, company.id, MockERPAdapter())

    assert first.vendors.created == 4
    assert first.invoices.created == 5
    assert second.vendors.created == 0
    assert second.vendors.skipped == 4
    assert second.invoices.created == 0
    assert second.invoices.skipped == 5
    assert await db_session.scalar(
        select(func.count(Supplier.id)).where(Supplier.company_id == company.id)
    ) == 4
    assert await db_session.scalar(
        select(func.count(Invoice.id)).where(Invoice.company_id == company.id)
    ) == 5
    assert await db_session.scalar(
        select(func.count(IntegrationConnection.id)).where(
            IntegrationConnection.company_id == company.id
        )
    ) == 1
    assert await db_session.scalar(
        select(func.count(IntegrationSyncRun.id)).where(
            IntegrationSyncRun.company_id == company.id
        )
    ) == 2
