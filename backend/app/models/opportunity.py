
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.core.enums import (
    OpportunityPriority,
    OpportunityStatus,
    OpportunityType,
    SourceType,
)
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.academy_resource import AcademyResource
    from app.models.company import Company
    from app.models.compliance_event import ComplianceEvent
    from app.models.contact import Contact
    from app.models.follow_up import FollowUp
    from app.models.interaction import Interaction
    from app.models.message_draft import MessageDraft
    from app.models.offer import Offer
    from app.models.opportunity_score import OpportunityScore


class Opportunity(BaseModel, table=True):
    __tablename__ = "opportunities"

    company_id: uuid.UUID = Field(foreign_key="companies.id", nullable=False)
    contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contacts.id")
    offer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="offers.id")
    academy_resource_id: Optional[uuid.UUID] = Field(default=None, foreign_key="academy_resources.id")
    title: str = Field(index=True, nullable=False)
    opportunity_type: OpportunityType = Field(default=OpportunityType.other)
    description: Optional[str] = Field(default=None)
    detected_need: Optional[str] = Field(default=None)
    source: SourceType = Field(default=SourceType.manual)
    source_url: Optional[str] = Field(default=None)
    source_published_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    location: Optional[str] = Field(default=None)
    language: str = Field(default="fr")
    status: OpportunityStatus = Field(default=OpportunityStatus.new)
    priority: OpportunityPriority = Field(default=OpportunityPriority.medium)
    score: Optional[int] = Field(default=None)
    recommended_landing_page: Optional[str] = Field(default=None)
    next_action: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)

    # relationships
    company: "Company" = Relationship(back_populates="opportunities")
    contact: Optional["Contact"] = Relationship(back_populates="opportunities")
    offer: Optional["Offer"] = Relationship(back_populates="opportunities")
    academy_resource: Optional["AcademyResource"] = Relationship(back_populates="opportunities")
    scores: list["OpportunityScore"] = Relationship(back_populates="opportunity")
    message_drafts: list["MessageDraft"] = Relationship(back_populates="opportunity")
    follow_ups: list["FollowUp"] = Relationship(back_populates="opportunity")
    interactions: list["Interaction"] = Relationship(back_populates="opportunity")
    compliance_events: list["ComplianceEvent"] = Relationship(back_populates="opportunity")
