from fastapi import APIRouter

from app.api.v1.endpoints import (
    academy_categories,
    academy_resources,
    companies,
    contacts,
    health,
    messages,
    offers,
    opportunities,
    service_categories,
)

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(service_categories.router, prefix="/service-categories", tags=["service-categories"])
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
router.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
router.include_router(offers.router, prefix="/offers", tags=["offers"])
router.include_router(academy_categories.router, prefix="/academy-categories", tags=["academy"])
router.include_router(academy_resources.router, prefix="/academy-resources", tags=["academy"])
router.include_router(messages.router, prefix="/message-drafts", tags=["messages"])
