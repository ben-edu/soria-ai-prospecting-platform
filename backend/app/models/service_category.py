
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.core.enums import ServiceCategoryStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.offer import Offer


class ServiceCategory(BaseModel, table=True):
    __tablename__ = "service_categories"

    name: str = Field(unique=True, index=True, nullable=False)
    slug: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None)
    position: int = Field(default=0)
    status: ServiceCategoryStatus = Field(default=ServiceCategoryStatus.active)
    is_active: bool = Field(default=True)

    # relationships
    offers: list["Offer"] = Relationship(back_populates="category")
