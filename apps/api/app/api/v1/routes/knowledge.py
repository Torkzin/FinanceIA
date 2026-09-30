from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import KnowledgeDocument, User
from app.db.models.enums import UserRole
from app.schemas.knowledge import (
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
)
from app.services.knowledge import (
    KnowledgeProcessingError,
    answer_knowledge_question,
    index_document,
)
from app.services.storage import knowledge_storage

router = APIRouter()
KnowledgeAdmin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("/documents", response_model=KnowledgeDocumentListResponse)
async def list_knowledge_documents(
    current_user: CurrentUser, session: SessionDependency
) -> KnowledgeDocumentListResponse:
    filters = [KnowledgeDocument.company_id == current_user.company_id]
    total = await session.scalar(select(func.count(KnowledgeDocument.id)).where(*filters))
    documents = await session.scalars(
        select(KnowledgeDocument)
        .where(*filters)
        .order_by(KnowledgeDocument.uploaded_at.desc())
        .limit(100)
    )
    return KnowledgeDocumentListResponse(
        items=[KnowledgeDocumentResponse.model_validate(item) for item in documents],
        total=total or 0,
    )


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge_document(
    admin: KnowledgeAdmin,
    session: SessionDependency,
    file: Annotated[UploadFile, File(description="Searchable PDF or TXT up to 10 MB")],
) -> KnowledgeDocumentResponse:
    document_id = uuid4()
    stored = await knowledge_storage.save(file, admin.company_id, document_id)
    existing = await session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.company_id == admin.company_id,
            KnowledgeDocument.sha256 == stored.sha256,
        )
    )
    if existing:
        knowledge_storage.delete(stored.storage_key)
        raise HTTPException(status_code=409, detail="This knowledge document was already uploaded")
    document = KnowledgeDocument(
        id=document_id,
        company_id=admin.company_id,
        original_name=(file.filename or "knowledge-document")[:255],
        storage_key=stored.storage_key,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        status="processing",
        uploaded_by_id=admin.id,
    )
    session.add(document)
    try:
        await session.flush()
        await index_document(session, document, knowledge_storage.resolve(document.storage_key))
        document.indexed_at = datetime.now(UTC)
        await session.commit()
    except KnowledgeProcessingError as exc:
        await session.rollback()
        document = KnowledgeDocument(
            id=document_id,
            company_id=admin.company_id,
            original_name=(file.filename or "knowledge-document")[:255],
            storage_key=stored.storage_key,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            status="failed",
            uploaded_by_id=admin.id,
            processing_error=str(exc)[:500],
        )
        session.add(document)
        await session.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        knowledge_storage.delete(stored.storage_key)
        raise HTTPException(
            status_code=409, detail="This knowledge document was already uploaded"
        ) from exc
    await session.refresh(document)
    return KnowledgeDocumentResponse.model_validate(document)


@router.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge_base(
    payload: KnowledgeQueryRequest,
    current_user: CurrentUser,
    session: SessionDependency,
) -> KnowledgeQueryResponse:
    try:
        return await answer_knowledge_question(
            payload.question, payload.limit, session, current_user.company_id
        )
    except KnowledgeProcessingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
