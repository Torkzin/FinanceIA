from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

AnomalySeverity = Literal["low", "medium", "high"]
AnomalyStatus = Literal["open", "reviewed", "dismissed"]


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    related_invoice_id: UUID
    anomaly_type: str
    severity: AnomalySeverity
    explanation: str
    metrics: dict[str, Any]
    status: AnomalyStatus
    detected_at: datetime
    ai_analysis: str | None
    ai_provider: str | None
    ai_model: str | None
    analyzed_at: datetime | None


class AnomalyListResponse(BaseModel):
    items: list[AnomalyResponse]
    total: int


class AnomalyDetectionResponse(BaseModel):
    detected: int
    created: int
    updated: int


class AnomalyAnalysisResponse(BaseModel):
    anomaly_id: UUID
    analysis: str
    provider: str
    model: str
    analyzed_at: datetime
