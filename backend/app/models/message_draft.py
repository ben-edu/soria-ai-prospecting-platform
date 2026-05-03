
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.core.enums import MessageStatus, MessageType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.opportunity import Opportunity


class MessageDraft(BaseModel, table=True):
    __tablename__ = "message_drafts"

    opportunity_id: uuid.UUID = Field(foreign_key="opportunities.id", nullable=False)
    contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contacts.id")
    message_type: MessageType = Field(default=MessageType.prospecting_email)
    language: str = Field(default="fr")
    subject: Optional[str] = Field(default=None)
    body: str = Field(nullable=False)
    tone: Optional[str] = Field(default=None)
    status: MessageStatus = Field(default=MessageStatus.draft)
    generated_by: str = Field(default="system")
    model_name: Optional[str] = Field(default=None)
    prompt_version: Optional[str] = Field(default=None)
    review_notes: Optional[str] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    sent_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # relationships
    opportunity: "Opportunity" = Relationship(back_populates="message_drafts")
    contact: Optional["Contact"] = Relationship(back_populates="message_drafts")
