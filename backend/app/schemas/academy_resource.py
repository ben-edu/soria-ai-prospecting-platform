from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import AcademyLevel, AcademyResourceType


class AcademyResourceCreate(BaseModel):
    category_id: Optional[UUID] = None
    title: str
    slug: str
    short_description: Optional[str] = None
    content: Optional[str] = None
    resource_type: AcademyResourceType = AcademyResourceType.guide
    level: AcademyLevel = AcademyLevel.beginner
    target_audience: Optional[dict[str, Any]] = None
    technologies: Optional[dict[str, Any]] = None
    public_url: Optional[str] = None
    academy_url: Optional[str] = None
    moodle_course_id: Optional[str] = None
    is_free: bool = True
    is_published: bool = False


class AcademyResourceUpdate(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    short_description: Optional[str] = None
    content: Optional[str] = None
    resource_type: Optional[AcademyResourceType] = None
    level: Optional[AcademyLevel] = None
    target_audience: Optional[dict[str, Any]] = None
    technologies: Optional[dict[str, Any]] = None
    public_url: Optional[str] = None
    academy_url: Optional[str] = None
    moodle_course_id: Optional[str] = None
    is_free: Optional[bool] = None
    is_published: Optional[bool] = None


class AcademyResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: Optional[UUID] = None
    title: str
    slug: str
    short_description: Optional[str] = None
    content: Optional[str] = None
    resource_type: AcademyResourceType
    level: AcademyLevel
    target_audience: Optional[dict[str, Any]] = None
    technologies: Optional[dict[str, Any]] = None
    public_url: Optional[str] = None
    academy_url: Optional[str] = None
    moodle_course_id: Optional[str] = None
    is_free: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime


class AcademyResourceListResponse(BaseModel):
    items: list[AcademyResourceRead]
    total: int
    skip: int
    limit: int
