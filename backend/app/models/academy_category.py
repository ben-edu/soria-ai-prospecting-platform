from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.academy_resource import AcademyResource


class AcademyCategory(BaseModel, table=True):
    __tablename__ = "academy_categories"

    name: str = Field(unique=True, index=True, nullable=False)
    slug: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    position: int = Field(default=0)
    is_active: bool = Field(default=True)

    # relationships
    resources: list["AcademyResource"] = Relationship(back_populates="category")
