
import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.core.enums import ComplianceEventType, SourceType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.opportunity import Opportunity


class ComplianceEvent(BaseModel, table=True):
    __tablename__ = "compliance_events"

    company_id: Optional[uuid.UUID] = Field(default=None, foreign_key="companies.id")
    contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contacts.id")
    opportunity_id: Optional[uuid.UUID] = Field(default=None, foreign_key="opportunities.id")
    event_type: ComplianceEventType = Field(nullable=False)
    source: SourceType = Field(default=SourceType.manual)
    source_url: Optional[str] = Field(default=None)
    reason_for_contact: Optional[str] = Field(default=None)
    professional_relevance: Optional[str] = Field(default=None)
    opt_out_status: bool = Field(default=False)
    notes: Optional[str] = Field(default=None)

    # relationships
    company: Optional["Company"] = Relationship(back_populates="compliance_events")
    contact: Optional["Contact"] = Relationship(back_populates="compliance_events")
    opportunity: Optional["Opportunity"] = Relationship(back_populates="compliance_events")
