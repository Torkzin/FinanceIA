from fastapi import APIRouter

from app.integrations.erp import MockERPAdapter
from app.schemas.erp import ERPInvoice, ERPVendor

router = APIRouter(prefix="/external-api", tags=["mock-erp"])


@router.get("/vendors", response_model=list[ERPVendor])
async def list_external_vendors() -> list[ERPVendor]:
    return (await MockERPAdapter().fetch_snapshot()).vendors


@router.get("/invoices", response_model=list[ERPInvoice])
async def list_external_invoices() -> list[ERPInvoice]:
    return (await MockERPAdapter().fetch_snapshot()).invoices
