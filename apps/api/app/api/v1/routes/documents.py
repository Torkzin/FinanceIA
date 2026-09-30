from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import CostCenter, FinancialDocument, Invoice, Supplier, User
from app.db.models.enums import UserRole
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.schemas.extraction import (
    ConfirmDocumentExtraction,
    DocumentExtractionResponse,
    ExtractedInvoiceData,
)
from app.schemas.invoice import InvoiceResponse
from app.services.ai_extraction import ExtractionUnavailableError, get_document_extractor
from app.services.financial_records import validate_invoice_references
from app.services.storage import document_storage

router = APIRouter()
DocumentWriter = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE))]


async def get_document_or_404(
    session: SessionDependency,
    company_id: UUID,
    document_id: UUID,
    *,
    for_update: bool = False,
) -> FinancialDocument:
    statement = select(FinancialDocument).where(
        FinancialDocument.id == document_id,
        FinancialDocument.company_id == company_id,
    )
    if for_update:
        statement = statement.with_for_update()
    document = await session.scalar(statement)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


async def extraction_response(
    session: SessionDependency, document: FinancialDocument
) -> DocumentExtractionResponse:
    data = (
        ExtractedInvoiceData.model_validate(document.extraction_data)
        if document.extraction_data
        else None
    )
    supplier_id = None
    cost_center_id = None
    if data and data.supplier_document_number:
        supplier_id = await session.scalar(
            select(Supplier.id).where(
                Supplier.company_id == document.company_id,
                Supplier.document_number == data.supplier_document_number,
            )
        )
    if data and not supplier_id and data.supplier_name:
        supplier_id = await session.scalar(
            select(Supplier.id).where(
                Supplier.company_id == document.company_id,
                func.lower(Supplier.name) == data.supplier_name.lower(),
            )
        )
    if data and data.cost_center_name:
        cost_center_id = await session.scalar(
            select(CostCenter.id).where(
                CostCenter.company_id == document.company_id,
                func.lower(CostCenter.name) == data.cost_center_name.lower(),
            )
        )
    return DocumentExtractionResponse(
        document_id=document.id,
        status=document.status,
        provider=document.extraction_provider,
        model=document.extraction_model,
        data=data,
        suggested_supplier_id=supplier_id,
        suggested_cost_center_id=cost_center_id,
        confirmed_invoice_id=document.confirmed_invoice_id,
        extracted_at=document.extracted_at,
        error=document.extraction_error,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser, session: SessionDependency
) -> DocumentListResponse:
    filters = [FinancialDocument.company_id == current_user.company_id]
    total = await session.scalar(select(func.count(FinancialDocument.id)).where(*filters))
    documents = await session.scalars(
        select(FinancialDocument)
        .where(*filters)
        .order_by(FinancialDocument.uploaded_at.desc())
        .limit(100)
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in documents],
        total=total or 0,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    writer: DocumentWriter,
    session: SessionDependency,
    file: Annotated[UploadFile, File(description="PDF, PNG, JPG, or JPEG up to 10 MB")],
) -> DocumentResponse:
    document_id = uuid4()
    stored = await document_storage.save(file, writer.company_id, document_id)
    existing = await session.scalar(
        select(FinancialDocument).where(
            FinancialDocument.company_id == writer.company_id,
            FinancialDocument.sha256 == stored.sha256,
        )
    )
    if existing:
        document_storage.delete(stored.storage_key)
        raise HTTPException(status_code=409, detail="This document was already uploaded")

    document = FinancialDocument(
        id=document_id,
        company_id=writer.company_id,
        original_name=(file.filename or "document")[:255],
        storage_key=stored.storage_key,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        status="uploaded",
        uploaded_by_id=writer.id,
    )
    session.add(document)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        document_storage.delete(stored.storage_key)
        raise HTTPException(status_code=409, detail="This document was already uploaded") from exc
    await session.refresh(document)
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: CurrentUser,
    session: SessionDependency,
) -> FileResponse:
    document = await get_document_or_404(session, current_user.company_id, document_id)
    path = document_storage.resolve(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path, media_type=document.media_type, filename=document.original_name)


@router.get("/{document_id}/extraction", response_model=DocumentExtractionResponse)
async def get_document_extraction(
    document_id: UUID,
    current_user: CurrentUser,
    session: SessionDependency,
) -> DocumentExtractionResponse:
    document = await get_document_or_404(session, current_user.company_id, document_id)
    return await extraction_response(session, document)


@router.post("/{document_id}/extract", response_model=DocumentExtractionResponse)
async def extract_document(
    document_id: UUID,
    writer: DocumentWriter,
    session: SessionDependency,
) -> DocumentExtractionResponse:
    document = await get_document_or_404(session, writer.company_id, document_id)
    if document.status == "completed":
        raise HTTPException(status_code=409, detail="Document extraction is already confirmed")
    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Document extraction is already in progress")
    if document.status == "review" and document.extraction_data:
        return await extraction_response(session, document)

    document.status = "processing"
    document.extraction_error = None
    await session.commit()
    try:
        extractor = get_document_extractor()
        result = await extractor.extract(
            document_storage.resolve(document.storage_key), document.media_type
        )
    except ExtractionUnavailableError as exc:
        document.status = "failed"
        document.extraction_error = str(exc)[:500]
        await session.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        document.status = "failed"
        document.extraction_error = "Unexpected extraction failure"
        await session.commit()
        raise HTTPException(status_code=500, detail="Unexpected extraction failure") from exc

    document.extraction_data = result.model_dump(mode="json")
    document.extraction_provider = extractor.provider
    document.extraction_model = extractor.model
    document.extracted_at = datetime.now(UTC)
    document.status = "review"
    await session.commit()
    await session.refresh(document)
    return await extraction_response(session, document)


@router.post(
    "/{document_id}/confirm",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_document_extraction(
    document_id: UUID,
    payload: ConfirmDocumentExtraction,
    writer: DocumentWriter,
    session: SessionDependency,
) -> InvoiceResponse:
    document = await get_document_or_404(session, writer.company_id, document_id, for_update=True)
    if document.status != "review" or not document.extraction_data:
        raise HTTPException(status_code=409, detail="Document is not ready for review")
    if document.confirmed_invoice_id:
        raise HTTPException(status_code=409, detail="Document was already confirmed")
    await validate_invoice_references(
        session, writer.company_id, payload.supplier_id, payload.cost_center_id
    )
    confidence = ExtractedInvoiceData.model_validate(document.extraction_data).confidence
    invoice = Invoice(
        company_id=writer.company_id,
        source="document",
        ai_confidence=confidence,
        **payload.model_dump(),
    )
    session.add(invoice)
    await session.flush()
    document.confirmed_invoice_id = invoice.id
    document.status = "completed"
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Invoice already exists or is invalid") from exc
    await session.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)
