from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.knowledge import KnowledgeSource

WorkflowRoute = Literal["finance", "knowledge", "anomalies", "documents"]


class WorkflowQueryRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)


class WorkflowQueryResponse(BaseModel):
    answer: str
    route: WorkflowRoute
    trace: list[str]
    sources: list[KnowledgeSource]
    metadata: dict[str, Any]
    validated: bool
