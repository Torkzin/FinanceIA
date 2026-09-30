from fastapi import APIRouter, HTTPException

from app.api.dependencies.auth import CurrentUser, SessionDependency
from app.schemas.workflow import WorkflowQueryRequest, WorkflowQueryResponse
from app.services.knowledge import KnowledgeProcessingError
from app.services.workflow import run_workflow

router = APIRouter()


@router.post("/query", response_model=WorkflowQueryResponse)
async def orchestrated_query(
    payload: WorkflowQueryRequest,
    current_user: CurrentUser,
    session: SessionDependency,
) -> WorkflowQueryResponse:
    try:
        return await run_workflow(payload.message, session, current_user.company_id)
    except (RuntimeError, KnowledgeProcessingError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
