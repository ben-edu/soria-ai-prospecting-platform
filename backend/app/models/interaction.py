
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.core.enums import InteractionDirection, InteractionType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.opportunity import Opportunity


class Interaction(BaseModel, table=True):
    __tablename__ = "interactions"

    opportunity_id: uuid.UUID = Field(foreign_key="opportunities.id", nullable=False)
    contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contacts.id")
    interaction_type: InteractionType = Field(default=InteractionType.note)
    direction: InteractionDirection = Field(default=InteractionDirection.internal)
    summary: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    happened_at: datetime = Field(nullable=False, sa_type=DateTime(timezone=True))

    # relationships
    opportunity: "Opportunity" = Relationship(back_populates="interactions")
    contact: Optional["Contact"] = Relationship(back_populates="interactions")
