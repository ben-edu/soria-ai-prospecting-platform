from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

from app.core.enums import ContactType, EmailVerificationStatus, SourceType


class ContactCreate(BaseModel):
    company_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    role_title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: ContactType = ContactType.unknown
    source: SourceType = SourceType.manual
    source_url: Optional[str] = None
    email_verification_status: EmailVerificationStatus = EmailVerificationStatus.unknown
    is_primary: bool = False
    opt_out: bool = False
    notes: Optional[str] = None

    @model_validator(mode="after")
    def generate_full_name(self):
        if not self.full_name and (self.first_name or self.last_name):
            parts = [p for p in (self.first_name, self.last_name) if p]
            self.full_name = " ".join(parts)
        return self


class ContactUpdate(BaseModel):
    company_id: Optional[UUID] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    role_title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: Optional[ContactType] = None
    source: Optional[SourceType] = None
    source_url: Optional[str] = None
    email_verification_status: Optional[EmailVerificationStatus] = None
    is_primary: Optional[bool] = None
    opt_out: Optional[bool] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def generate_full_name(self):
        if not self.full_name and (self.first_name or self.last_name):
            parts = [p for p in (self.first_name, self.last_name) if p]
            self.full_name = " ".join(parts)
        return self


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    role_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: ContactType
    source: SourceType
    source_url: Optional[str] = None
    email_verification_status: EmailVerificationStatus
    is_primary: bool
    opt_out: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    items: list[ContactRead]
    total: int
    skip: int
    limit: int
