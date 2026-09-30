from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostCenterCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    description: str | None = Field(default=None, max_length=1000)


class CostCenterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    description: str | None = Field(default=None, max_length=1000)


class CostCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str
    description: str | None


class CostCenterListResponse(BaseModel):
    items: list[CostCenterResponse]
    total: int
    page: int
    page_size: int
