"""Academy resources endpoint."""

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.academy_resource import AcademyResource

router = APIRouter()


@router.get("", response_model=List[AcademyResource])
def list_academy_resources(db: Session = Depends(get_db)):
    resources = db.exec(select(AcademyResource)).all()
    return resources
