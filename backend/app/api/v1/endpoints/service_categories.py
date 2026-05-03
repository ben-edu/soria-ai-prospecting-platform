from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.service_category import ServiceCategory

router = APIRouter()


@router.get("", response_model=List[ServiceCategory])
def list_service_categories(db: Session = Depends(get_db)):
    categories = db.exec(select(ServiceCategory)).all()
    return categories
