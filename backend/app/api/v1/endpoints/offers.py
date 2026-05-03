from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.offer import Offer

router = APIRouter()


@router.get("", response_model=List[Offer])
def list_offers(db: Session = Depends(get_db)):
    offers = db.exec(select(Offer)).all()
    return offers
