"""Academy categories endpoint."""

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.academy_category import AcademyCategory

router = APIRouter()


@router.get("", response_model=List[AcademyCategory])
def list_academy_categories(db: Session = Depends(get_db)):
    categories = db.exec(select(AcademyCategory)).all()
    return categories
