from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import CompanyStatus, CompanyType, SourceType


class CompanyCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    website_url: Optional[str] = None
    domain: Optional[str] = None
    company_type: CompanyType = CompanyType.unknown
    sector: Optional[str] = None
    size_label: Optional[str] = None
    employee_count: Optional[int] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: str = "France"
    source: SourceType = SourceType.manual
    source_url: Optional[str] = None
    notes: Optional[str] = None
    status: CompanyStatus = CompanyStatus.new


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    website_url: Optional[str] = None
    domain: Optional[str] = None
    company_type: Optional[CompanyType] = None
    sector: Optional[str] = None
    size_label: Optional[str] = None
    employee_count: Optional[int] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    source: Optional[SourceType] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[CompanyStatus] = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: Optional[str] = None
    website_url: Optional[str] = None
    domain: Optional[str] = None
    company_type: CompanyType
    sector: Optional[str] = None
    size_label: Optional[str] = None
    employee_count: Optional[int] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: str
    source: SourceType
    source_url: Optional[str] = None
    notes: Optional[str] = None
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    items: list[CompanyRead]
    total: int
    skip: int
    limit: int
