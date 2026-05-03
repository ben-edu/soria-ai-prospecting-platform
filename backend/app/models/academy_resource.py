
import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import JSON, Field, Relationship

from app.core.enums import AcademyLevel, AcademyResourceType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.academy_category import AcademyCategory
    from app.models.opportunity import Opportunity


class AcademyResource(BaseModel, table=True):
    __tablename__ = "academy_resources"

    category_id: Optional[uuid.UUID] = Field(default=None, foreign_key="academy_categories.id")
    title: str = Field(index=True, nullable=False)
    slug: str = Field(unique=True, index=True, nullable=False)
    short_description: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    resource_type: AcademyResourceType = Field(default=AcademyResourceType.guide)
    level: AcademyLevel = Field(default=AcademyLevel.beginner)
    target_audience: Optional[dict] = Field(default=None, sa_type=JSON)
    technologies: Optional[dict] = Field(default=None, sa_type=JSON)
    public_url: Optional[str] = Field(default=None)
    academy_url: Optional[str] = Field(default=None)
    moodle_course_id: Optional[str] = Field(default=None)
    is_free: bool = Field(default=True)
    is_published: bool = Field(default=False)

    # relationships
    category: Optional["AcademyCategory"] = Relationship(back_populates="resources")
    opportunities: list["Opportunity"] = Relationship(back_populates="academy_resource")
