from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.company import Company

router = APIRouter()


@router.get("", response_model=List[Company])
def list_companies(db: Session = Depends(get_db)):
    companies = db.exec(select(Company)).all()
    return companies


@router.post("", response_model=Company)
def create_company(company: Company, db: Session = Depends(get_db)):
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
