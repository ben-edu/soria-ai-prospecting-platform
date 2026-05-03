
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.core.enums import FollowUpActionType, FollowUpStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.opportunity import Opportunity


class FollowUp(BaseModel, table=True):
    __tablename__ = "follow_ups"

    opportunity_id: uuid.UUID = Field(foreign_key="opportunities.id", nullable=False)
    contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contacts.id")
    due_date: datetime = Field(nullable=False, sa_type=DateTime(timezone=True))
    action_type: FollowUpActionType = Field(default=FollowUpActionType.send_follow_up)
    status: FollowUpStatus = Field(default=FollowUpStatus.planned)
    notes: Optional[str] = Field(default=None)
    openproject_work_package_id: Optional[str] = Field(default=None)

    # relationships
    opportunity: "Opportunity" = Relationship(back_populates="follow_ups")
    contact: Optional["Contact"] = Relationship(back_populates="follow_ups")
