from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OfferCreate(BaseModel):
    category_id: UUID
    name: str
    slug: str
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    target_audience: Optional[dict[str, Any]] = None
    keywords: Optional[dict[str, Any]] = None
    landing_page_url: Optional[str] = None
    priority: int = 0
    is_active: bool = True


class OfferUpdate(BaseModel):
    category_id: Optional[UUID] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    target_audience: Optional[dict[str, Any]] = None
    keywords: Optional[dict[str, Any]] = None
    landing_page_url: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class OfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    name: str
    slug: str
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    target_audience: Optional[dict[str, Any]] = None
    keywords: Optional[dict[str, Any]] = None
    landing_page_url: Optional[str] = None
    priority: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OfferListResponse(BaseModel):
    items: list[OfferRead]
    total: int
    skip: int
    limit: int
