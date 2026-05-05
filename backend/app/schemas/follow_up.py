from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FollowUpActionType, FollowUpStatus


class FollowUpCreate(BaseModel):
    opportunity_id: UUID
    contact_id: Optional[UUID] = None
    due_date: datetime
    action_type: FollowUpActionType = FollowUpActionType.send_follow_up
    status: FollowUpStatus = FollowUpStatus.planned
    notes: Optional[str] = None
    openproject_work_package_id: Optional[str] = None


class FollowUpUpdate(BaseModel):
    contact_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    action_type: Optional[FollowUpActionType] = None
    status: Optional[FollowUpStatus] = None
    notes: Optional[str] = None
    openproject_work_package_id: Optional[str] = None


class FollowUpRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    contact_id: Optional[UUID] = None
    due_date: datetime
    action_type: FollowUpActionType
    status: FollowUpStatus
    notes: Optional[str] = None
    openproject_work_package_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FollowUpListResponse(BaseModel):
    items: list[FollowUpRead]
    total: int
    skip: int
    limit: int
