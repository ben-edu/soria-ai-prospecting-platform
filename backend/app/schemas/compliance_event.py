from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import ComplianceEventType, SourceType


class ComplianceEventCreate(BaseModel):
    company_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    event_type: ComplianceEventType
    source: SourceType = SourceType.manual
    source_url: Optional[str] = None
    reason_for_contact: Optional[str] = None
    professional_relevance: Optional[str] = None
    opt_out_status: bool = False
    notes: Optional[str] = None


class ComplianceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    event_type: ComplianceEventType
    source: SourceType
    source_url: Optional[str] = None
    reason_for_contact: Optional[str] = None
    professional_relevance: Optional[str] = None
    opt_out_status: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ComplianceEventListResponse(BaseModel):
    items: list[ComplianceEventRead]
    total: int
    skip: int
    limit: int
