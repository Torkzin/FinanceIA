from typing import Any

from pydantic import BaseModel, Field


class FinancialChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)


class FinancialChatResponse(BaseModel):
    answer: str
    tool: str
    data: dict[str, Any]
    provider: str
    model: str
