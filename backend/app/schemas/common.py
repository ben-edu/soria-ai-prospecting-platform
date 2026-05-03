from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    detail: str


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UUIDMixin(BaseModel):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
