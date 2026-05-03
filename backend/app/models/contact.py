
import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.core.enums import ContactType, EmailVerificationStatus, SourceType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.compliance_event import ComplianceEvent
    from app.models.follow_up import FollowUp
    from app.models.interaction import Interaction
    from app.models.message_draft import MessageDraft
    from app.models.opportunity import Opportunity


class Contact(BaseModel, table=True):
    __tablename__ = "contacts"

    company_id: uuid.UUID = Field(foreign_key="companies.id", nullable=False)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None, index=True)
    role_title: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, index=True)
    phone: Optional[str] = Field(default=None)
    linkedin_url: Optional[str] = Field(default=None)
    contact_type: ContactType = Field(default=ContactType.unknown)
    source: SourceType = Field(default=SourceType.manual)
    source_url: Optional[str] = Field(default=None)
    email_verification_status: EmailVerificationStatus = Field(default=EmailVerificationStatus.unknown)
    is_primary: bool = Field(default=False)
    opt_out: bool = Field(default=False)
    notes: Optional[str] = Field(default=None)

    # relationships
    company: "Company" = Relationship(back_populates="contacts")
    opportunities: list["Opportunity"] = Relationship(back_populates="contact")
    message_drafts: list["MessageDraft"] = Relationship(back_populates="contact")
    follow_ups: list["FollowUp"] = Relationship(back_populates="contact")
    interactions: list["Interaction"] = Relationship(back_populates="contact")
    compliance_events: list["ComplianceEvent"] = Relationship(back_populates="contact")
