from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import ServiceCategoryStatus
from app.models.service_category import ServiceCategory

router = APIRouter()


class ServiceCategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    position: int = 0
    status: ServiceCategoryStatus = ServiceCategoryStatus.active
    is_active: bool = True


@router.get("", response_model=List[ServiceCategory])
def list_service_categories(db: Session = Depends(get_db)):
    categories = db.exec(select(ServiceCategory)).all()
    return categories


@router.post("", response_model=ServiceCategory, status_code=201)
def create_service_category(data: ServiceCategoryCreate, db: Session = Depends(get_db)):
    # Check slug uniqueness
    existing = db.exec(select(ServiceCategory).where(ServiceCategory.slug == data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="A service category with this slug already exists")

    category = ServiceCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
