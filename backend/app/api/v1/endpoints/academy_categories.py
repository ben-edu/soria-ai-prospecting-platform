"""Academy categories endpoint."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.academy_category import AcademyCategory

router = APIRouter()


class AcademyCategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    content: Optional[str] = None
    position: int = 0
    is_active: bool = True


@router.get("", response_model=List[AcademyCategory])
def list_academy_categories(db: Session = Depends(get_db)):
    categories = db.exec(select(AcademyCategory)).all()
    return categories


@router.post("", response_model=AcademyCategory, status_code=201)
def create_academy_category(data: AcademyCategoryCreate, db: Session = Depends(get_db)):
    # Check slug uniqueness
    existing = db.exec(select(AcademyCategory).where(AcademyCategory.slug == data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="An academy category with this slug already exists")

    category = AcademyCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
