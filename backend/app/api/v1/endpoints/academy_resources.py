"""Academy resources endpoint."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import AcademyLevel, AcademyResourceType
from app.models.academy_category import AcademyCategory
from app.models.academy_resource import AcademyResource
from app.schemas.academy_resource import (
    AcademyResourceCreate,
    AcademyResourceListResponse,
    AcademyResourceRead,
    AcademyResourceUpdate,
)

router = APIRouter()


@router.get("", response_model=AcademyResourceListResponse)
def list_academy_resources(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    resource_type: Optional[AcademyResourceType] = Query(None),
    level: Optional[AcademyLevel] = Query(None),
    active: Optional[bool] = Query(None),
):
    conditions = []

    if search:
        like_pattern = f"%{search}%"
        conditions.append(
            AcademyResource.title.ilike(like_pattern)
            | AcademyResource.short_description.ilike(like_pattern)
            | AcademyResource.content.ilike(like_pattern)
        )

    if category_id is not None:
        try:
            import uuid

            conditions.append(AcademyResource.category_id == uuid.UUID(category_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category ID format")

    if resource_type is not None:
        conditions.append(AcademyResource.resource_type == resource_type)

    if level is not None:
        conditions.append(AcademyResource.level == level)

    if active is not None:
        conditions.append(AcademyResource.is_published == active)

    count_stmt = select(func.count(AcademyResource.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(AcademyResource)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return AcademyResourceListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=AcademyResourceRead, status_code=201)
def create_academy_resource(data: AcademyResourceCreate, db: Session = Depends(get_db)):
    # Validate category exists if provided
    if data.category_id is not None:
        category = db.get(AcademyCategory, data.category_id)
        if not category:
            raise HTTPException(status_code=400, detail="Referenced academy category does not exist")

    # Check slug uniqueness
    existing = db.exec(select(AcademyResource).where(AcademyResource.slug == data.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="An academy resource with this slug already exists")

    resource = AcademyResource(**data.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/{resource_id}", response_model=AcademyResourceRead)
def get_academy_resource(resource_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid academy resource ID format")

    resource = db.get(AcademyResource, uid)
    if not resource:
        raise HTTPException(status_code=404, detail="Academy resource not found")
    return resource


@router.patch("/{resource_id}", response_model=AcademyResourceRead)
def update_academy_resource(resource_id: str, data: AcademyResourceUpdate, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid academy resource ID format")

    resource = db.get(AcademyResource, uid)
    if not resource:
        raise HTTPException(status_code=404, detail="Academy resource not found")

    # Validate category if changed
    if data.category_id is not None and data.category_id != resource.category_id:
        category = db.get(AcademyCategory, data.category_id)
        if not category:
            raise HTTPException(status_code=400, detail="Referenced academy category does not exist")

    # Check slug uniqueness if changed
    if data.slug is not None and data.slug != resource.slug:
        existing = db.exec(select(AcademyResource).where(AcademyResource.slug == data.slug)).first()
        if existing:
            raise HTTPException(status_code=400, detail="An academy resource with this slug already exists")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(resource, key, value)

    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
