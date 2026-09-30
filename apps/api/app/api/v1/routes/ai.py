from fastapi import APIRouter, HTTPException

from app.api.dependencies.auth import CurrentUser, SessionDependency
from app.schemas.assistant import FinancialChatRequest, FinancialChatResponse
from app.services.financial_assistant import ask_financial_assistant

router = APIRouter()


@router.post("/chat", response_model=FinancialChatResponse)
async def financial_chat(
    payload: FinancialChatRequest,
    current_user: CurrentUser,
    session: SessionDependency,
) -> FinancialChatResponse:
    try:
        return await ask_financial_assistant(payload.message, session, current_user.company_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
