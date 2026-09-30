from fastapi import APIRouter

from app.api.dependencies.auth import CurrentUser, SessionDependency
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import build_dashboard

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def dashboard(current_user: CurrentUser, session: SessionDependency) -> DashboardResponse:
    return await build_dashboard(session, current_user.company_id)
