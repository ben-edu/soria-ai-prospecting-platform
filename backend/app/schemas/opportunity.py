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
    openproject_work_package_id: Optional[str] = None

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
    openproject_work_package_id: Optional[str] = None

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
    openproject_work_package_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: int
    explanation: str
    breakdown: dict[str, int]
    opportunity: OpportunityRead


class EnrichResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity: OpportunityRead
    detected_need: str
    recommended_landing_page: str
    next_action: str
    explanation: str
    applied: bool
    detected_need_overwritten: bool


class OpportunityListResponse(BaseModel):
    items: list[OpportunityRead]
    total: int
    skip: int
    limit: int


class MatchAssetOffer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    short_description: Optional[str] = None
    landing_page_url: Optional[str] = None
    is_active: bool


class MatchAssetResource(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    short_description: Optional[str] = None
    resource_type: str
    level: str
    public_url: Optional[str] = None
    academy_url: Optional[str] = None
    is_published: bool


class MatchAssetsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity: OpportunityRead
    offer: Optional[MatchAssetOffer] = None
    academy_resource: Optional[MatchAssetResource] = None
    explanation: str
    applied: bool


class OpenProjectWorkPackagePreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity: OpportunityRead
    suggested_type: str
    suggested_status: str
    suggested_priority: str
    subject: str
    description: str
    copy_hint: str


class AiDraftPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity: OpportunityRead
    provider: str
    model_name: str
    prompt_version: str
    prompt_profile: str = "prospecting_fr_v1"
    subject: str
    body: str
    safety_note: str
    copy_hint: str


class AiProviderDiagnosticsResponse(BaseModel):
    """Diagnostics information about the AI provider configuration.

    Returned by GET /api/v1/opportunities/ai-diagnostics/provider.
    No database records are created or mutated.
    """

    configured_provider: str
    configured_model_name: str
    configured_prompt_profile: str
    configured_prompt_version: str
    available_providers: list[str]
    provider_available: bool
    status: str
    message: str
