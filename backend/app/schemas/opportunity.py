from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import (
    OpportunityPriority,
    OpportunityStatus,
    OpportunityType,
    SourceType,
)


class OpportunityCreate(BaseModel):
    company_id: UUID
    contact_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None
    academy_resource_id: Optional[UUID] = None
    title: str
    opportunity_type: OpportunityType = OpportunityType.other
    description: Optional[str] = None
    detected_need: Optional[str] = None
    source: SourceType = SourceType.manual
    source_url: Optional[str] = None
    source_published_at: Optional[datetime] = None
    location: Optional[str] = None
    language: str = "fr"
    status: OpportunityStatus = OpportunityStatus.new
    priority: OpportunityPriority = OpportunityPriority.medium
    score: Optional[int] = None
    recommended_landing_page: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("score")
    @classmethod
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Score must be between 0 and 100")
        return v


class OpportunityUpdate(BaseModel):
    company_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None
    academy_resource_id: Optional[UUID] = None
    title: Optional[str] = None
    opportunity_type: Optional[OpportunityType] = None
    description: Optional[str] = None
    detected_need: Optional[str] = None
    source: Optional[SourceType] = None
    source_url: Optional[str] = None
    source_published_at: Optional[datetime] = None
    location: Optional[str] = None
    language: Optional[str] = None
    status: Optional[OpportunityStatus] = None
    priority: Optional[OpportunityPriority] = None
    score: Optional[int] = None
    recommended_landing_page: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("score")
    @classmethod
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Score must be between 0 and 100")
        return v


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    contact_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None
    academy_resource_id: Optional[UUID] = None
    title: str
    opportunity_type: OpportunityType
    description: Optional[str] = None
    detected_need: Optional[str] = None
    source: SourceType
    source_url: Optional[str] = None
    source_published_at: Optional[datetime] = None
    location: Optional[str] = None
    language: str
    status: OpportunityStatus
    priority: OpportunityPriority
    score: Optional[int] = None
    recommended_landing_page: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OpportunityListResponse(BaseModel):
    items: list[OpportunityRead]
    total: int
    skip: int
    limit: int
