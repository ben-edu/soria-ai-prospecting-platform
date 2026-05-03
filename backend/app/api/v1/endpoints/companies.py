from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import CompanyStatus, CompanyType
from app.models.company import Company
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyRead,
    CompanyUpdate,
)

router = APIRouter()


@router.get("", response_model=CompanyListResponse)
def list_companies(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[CompanyStatus] = Query(None),
    company_type: Optional[CompanyType] = Query(None),
    country: Optional[str] = Query(None),
):
    conditions = []

    if search:
        like_pattern = f"%{search}%"
        conditions.append(
            Company.name.ilike(like_pattern)
            | Company.domain.ilike(like_pattern)
            | Company.city.ilike(like_pattern)
        )

    if status:
        conditions.append(Company.status == status)

    if company_type:
        conditions.append(Company.company_type == company_type)

    if country:
        conditions.append(Company.country == country)

    count_stmt = select(func.count(Company.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(Company)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return CompanyListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID format")

    company = db.get(Company, uid)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(company_id: str, data: CompanyUpdate, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID format")

    company = db.get(Company, uid)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)

    db.add(company)
    db.commit()
    db.refresh(company)
    return company
