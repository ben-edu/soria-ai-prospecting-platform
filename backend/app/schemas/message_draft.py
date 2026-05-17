from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import MessageStatus, MessageType


class MessageDraftCreate(BaseModel):
    opportunity_id: UUID
    contact_id: Optional[UUID] = None
    message_type: MessageType = MessageType.prospecting_email
    language: str = "fr"
    subject: Optional[str] = None
    body: str
    tone: Optional[str] = None
    status: MessageStatus = MessageStatus.draft
    generated_by: str = "manual"
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    ai_provider: Optional[str] = None
    prompt_profile: Optional[str] = None

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("body must not be empty")
        return v

    @field_validator("status")
    @classmethod
    def validate_status_on_create(cls, v):
        if v not in (MessageStatus.draft, MessageStatus.needs_review):
            raise ValueError("Status on creation must be draft or needs_review")
        return v


class MessageDraftUpdate(BaseModel):
    contact_id: Optional[UUID] = None
    message_type: Optional[MessageType] = None
    language: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    tone: Optional[str] = None
    review_notes: Optional[str] = None

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("body must not be empty")
        return v


class MessageDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    contact_id: Optional[UUID] = None
    message_type: MessageType
    language: str
    subject: Optional[str] = None
    body: str
    tone: Optional[str] = None
    status: MessageStatus
    generated_by: str
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    ai_provider: Optional[str] = None
    prompt_profile: Optional[str] = None
    review_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MessageDraftListResponse(BaseModel):
    items: list[MessageDraftRead]
    total: int
    skip: int
    limit: int


class MessageDraftActionRequest(BaseModel):
    review_notes: Optional[str] = None


class DeliveryHelperResponse(BaseModel):
    """Read-only delivery helper info for a message draft.

    Determines the best channel for sending the draft based on
    available contact email and opportunity source URL.
    Never sends email server-side.
    """

    draft_id: UUID
    opportunity_id: UUID
    subject: Optional[str] = None
    body: str
    recipient_email: Optional[str] = None
    source_url: Optional[str] = None
    channel: str  # "email" | "platform_message" | "application_url" | "manual_research"
    recipient_status: str  # "email_available" | "email_missing"
    recommended_action: str
    mailto_url: Optional[str] = None
    copy_mode: str  # "email" | "platform" | "manual"
    warning: Optional[str] = None
