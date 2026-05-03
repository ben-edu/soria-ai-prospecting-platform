from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.opportunity import Opportunity

router = APIRouter()


@router.get("", response_model=List[Opportunity])
def list_opportunities(db: Session = Depends(get_db)):
    opportunities = db.exec(select(Opportunity)).all()
    return opportunities


@router.post("", response_model=Opportunity)
def create_opportunity(opportunity: Opportunity, db: Session = Depends(get_db)):
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity
