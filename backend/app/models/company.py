
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.core.enums import CompanyStatus, CompanyType, SourceType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.compliance_event import ComplianceEvent
    from app.models.contact import Contact
    from app.models.opportunity import Opportunity


class Company(BaseModel, table=True):
    __tablename__ = "companies"

    name: str = Field(index=True, nullable=False)
    slug: Optional[str] = Field(default=None, unique=True, index=True)
    website_url: Optional[str] = Field(default=None)
    domain: Optional[str] = Field(default=None, index=True)
    company_type: CompanyType = Field(default=CompanyType.unknown)
    sector: Optional[str] = Field(default=None)
    size_label: Optional[str] = Field(default=None)
    employee_count: Optional[int] = Field(default=None)
    city: Optional[str] = Field(default=None)
    region: Optional[str] = Field(default=None)
    country: str = Field(default="France")
    source: SourceType = Field(default=SourceType.manual)
    source_url: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    status: CompanyStatus = Field(default=CompanyStatus.new)

    # relationships
    contacts: list["Contact"] = Relationship(back_populates="company")
    opportunities: list["Opportunity"] = Relationship(back_populates="company")
    compliance_events: list["ComplianceEvent"] = Relationship(back_populates="company")
