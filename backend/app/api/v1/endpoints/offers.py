from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.offer import Offer
from app.models.service_category import ServiceCategory
from app.schemas.offer import OfferCreate, OfferListResponse, OfferRead, OfferUpdate

router = APIRouter()


@router.get("", response_model=OfferListResponse)
def list_offers(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
):
    conditions = []

    if search:
        like_pattern = f"%{search}%"
        conditions.append(
            Offer.name.ilike(like_pattern)
            | Offer.short_description.ilike(like_pattern)
            | Offer.full_description.ilike(like_pattern)
        )

    if category_id is not None:
        try:
            import uuid

            conditions.append(Offer.category_id == uuid.UUID(category_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category ID format")

    if active is not None:
        conditions.append(Offer.is_active == active)

    count_stmt = select(func.count(Offer.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(Offer)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return OfferListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=OfferRead, status_code=201)
def create_offer(data: OfferCreate, db: Session = Depends(get_db)):
    # Validate category exists
    category = db.get(ServiceCategory, data.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Referenced service category does not exist")

    # Check slug uniqueness
    existing = db.exec(select(Offer).where(Offer.slug == data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="An offer with this slug already exists")

    offer = Offer(**data.model_dump())
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.get("/{offer_id}", response_model=OfferRead)
def get_offer(offer_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(offer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid offer ID format")

    offer = db.get(Offer, uid)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


@router.patch("/{offer_id}", response_model=OfferRead)
def update_offer(offer_id: str, data: OfferUpdate, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(offer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid offer ID format")

    offer = db.get(Offer, uid)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Validate category if changed
    if data.category_id is not None and data.category_id != offer.category_id:
        category = db.get(ServiceCategory, data.category_id)
        if not category:
            raise HTTPException(status_code=400, detail="Referenced service category does not exist")

    # Check slug uniqueness if changed
    if data.slug is not None and data.slug != offer.slug:
        existing = db.exec(select(Offer).where(Offer.slug == data.slug)).first()
        if existing:
            raise HTTPException(status_code=400, detail="An offer with this slug already exists")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(offer, key, value)

    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer
