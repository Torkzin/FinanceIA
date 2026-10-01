import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CostCenter,
    IntegrationConnection,
    IntegrationSyncRun,
    Invoice,
    Supplier,
)
from app.db.models.enums import InvoiceSource
from app.integrations.erp import ERPAdapter
from app.schemas.erp import (
    ERPConnectionState,
    ERPPreviewResponse,
    ERPSyncCounts,
    ERPSyncResponse,
)

logger = logging.getLogger(__name__)
PROVIDER = "erp"


async def get_connection(
    session: AsyncSession, company_id: UUID
) -> IntegrationConnection | None:
    return await session.scalar(
        select(IntegrationConnection).where(
            IntegrationConnection.company_id == company_id,
            IntegrationConnection.provider == PROVIDER,
        )
    )


async def preview_erp(
    session: AsyncSession, company_id: UUID, adapter: ERPAdapter
) -> ERPPreviewResponse:
    snapshot = await adapter.fetch_snapshot()
    connection = await get_connection(session, company_id)
    state = None
    if connection:
        state = ERPConnectionState(
            adapter=connection.adapter,
            status=connection.status,
            checkpoint=connection.checkpoint,
            last_sync_at=connection.last_sync_at,
            last_sync_status=connection.last_sync_status,
        )
    return ERPPreviewResponse(
        source=snapshot.source,
        generated_at=snapshot.generated_at,
        vendor_count=len(snapshot.vendors),
        invoice_count=len(snapshot.invoices),
        connection=state,
    )


async def _ensure_connection(
    session: AsyncSession, company_id: UUID, adapter: ERPAdapter
) -> IntegrationConnection:
    connection = await get_connection(session, company_id)
    if connection:
        if connection.adapter != adapter.name:
            connection.adapter = adapter.name
        return connection
    connection = IntegrationConnection(
        id=uuid4(),
        company_id=company_id,
        provider=PROVIDER,
        adapter=adapter.name,
        status="active",
    )
    session.add(connection)
    return connection


def _supplier_changed(supplier: Supplier, values: dict[str, str | None]) -> bool:
    return any(getattr(supplier, field) != value for field, value in values.items())


def _invoice_changed(invoice: Invoice, values: dict[str, object]) -> bool:
    return any(getattr(invoice, field) != value for field, value in values.items())


async def sync_erp(
    session: AsyncSession, company_id: UUID, adapter: ERPAdapter
) -> ERPSyncResponse:
    started_at = datetime.now(UTC)
    connection = await _ensure_connection(session, company_id, adapter)
    await session.commit()

    try:
        snapshot = await adapter.fetch_snapshot()
        vendor_counts = ERPSyncCounts(received=len(snapshot.vendors))
        invoice_counts = ERPSyncCounts(received=len(snapshot.invoices))
        warnings: list[str] = []

        suppliers = list(
            await session.scalars(select(Supplier).where(Supplier.company_id == company_id))
        )
        suppliers_by_document = {item.document_number: item for item in suppliers}
        suppliers_by_external_id: dict[str, Supplier] = {}

        for vendor in snapshot.vendors:
            values = {
                "name": vendor.name,
                "email": str(vendor.email) if vendor.email else None,
                "category": vendor.category,
                "status": vendor.status,
            }
            supplier = suppliers_by_document.get(vendor.document_number)
            if supplier is None:
                supplier = Supplier(
                    company_id=company_id,
                    document_number=vendor.document_number,
                    **values,
                )
                session.add(supplier)
                suppliers_by_document[vendor.document_number] = supplier
                vendor_counts.created += 1
            elif _supplier_changed(supplier, values):
                for field, value in values.items():
                    setattr(supplier, field, value)
                vendor_counts.updated += 1
            else:
                vendor_counts.skipped += 1
            suppliers_by_external_id[vendor.external_id] = supplier

        await session.flush()
        cost_centers = list(
            await session.scalars(select(CostCenter).where(CostCenter.company_id == company_id))
        )
        cost_centers_by_code = {item.code: item for item in cost_centers}
        existing_invoices = list(
            await session.scalars(select(Invoice).where(Invoice.company_id == company_id))
        )
        invoices_by_key = {
            (invoice.supplier_id, invoice.invoice_number): invoice
            for invoice in existing_invoices
        }

        for external_invoice in snapshot.invoices:
            supplier = suppliers_by_external_id[external_invoice.vendor_external_id]
            cost_center = (
                cost_centers_by_code.get(external_invoice.cost_center_code)
                if external_invoice.cost_center_code
                else None
            )
            if external_invoice.cost_center_code and cost_center is None:
                warnings.append(
                    f"Centro de custo {external_invoice.cost_center_code} não encontrado para "
                    f"{external_invoice.invoice_number}; fatura importada sem alocação."
                )
            values: dict[str, object] = {
                "cost_center_id": cost_center.id if cost_center else None,
                "description": external_invoice.description,
                "category": external_invoice.category,
                "issue_date": external_invoice.issue_date,
                "due_date": external_invoice.due_date,
                "amount": Decimal(external_invoice.amount),
                "currency": external_invoice.currency,
                "status": external_invoice.status,
            }
            key = (supplier.id, external_invoice.invoice_number)
            invoice = invoices_by_key.get(key)
            if invoice is None:
                invoice = Invoice(
                    company_id=company_id,
                    supplier_id=supplier.id,
                    invoice_number=external_invoice.invoice_number,
                    source=InvoiceSource.ERP,
                    ai_confidence=None,
                    **values,
                )
                session.add(invoice)
                invoices_by_key[key] = invoice
                invoice_counts.created += 1
            elif invoice.source != InvoiceSource.ERP:
                invoice_counts.skipped += 1
                warnings.append(
                    f"{external_invoice.invoice_number} já existe com origem {invoice.source} "
                    "e não foi sobrescrita."
                )
            elif _invoice_changed(invoice, values):
                for field, value in values.items():
                    setattr(invoice, field, value)
                invoice_counts.updated += 1
            else:
                invoice_counts.skipped += 1

        completed_at = datetime.now(UTC)
        checkpoint = f"{snapshot.source}:{completed_at.isoformat()}"
        summary = {
            "source": snapshot.source,
            "vendors": vendor_counts.model_dump(),
            "invoices": invoice_counts.model_dump(),
            "warnings": warnings,
        }
        run = IntegrationSyncRun(
            id=uuid4(),
            company_id=company_id,
            connection_id=connection.id,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            summary=summary,
        )
        connection.checkpoint = checkpoint
        connection.last_sync_at = completed_at
        connection.last_sync_status = "completed"
        connection.last_summary = summary
        session.add(run)
        await session.commit()
        logger.info(
            "erp_sync_completed company=%s vendors_created=%s invoices_created=%s",
            company_id,
            vendor_counts.created,
            invoice_counts.created,
        )
        return ERPSyncResponse(
            run_id=run.id,
            source=snapshot.source,
            checkpoint=checkpoint,
            vendors=vendor_counts,
            invoices=invoice_counts,
            warnings=warnings,
            completed_at=completed_at,
        )
    except Exception as exc:
        await session.rollback()
        failed_at = datetime.now(UTC)
        connection = await _ensure_connection(session, company_id, adapter)
        connection.last_sync_at = failed_at
        connection.last_sync_status = "failed"
        failure = IntegrationSyncRun(
            id=uuid4(),
            company_id=company_id,
            connection_id=connection.id,
            status="failed",
            started_at=started_at,
            completed_at=failed_at,
            summary={"source": adapter.name},
            error_message=str(exc)[:500],
        )
        session.add(failure)
        await session.commit()
        logger.exception("erp_sync_failed company=%s", company_id)
        raise
