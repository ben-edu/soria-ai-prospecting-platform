from fastapi import APIRouter

from app.api.v1.endpoints import (
    academy_categories,
    academy_resources,
    companies,
    compliance_events,
    contacts,
    external_sources,
    follow_ups,
    health,
    messages,
    offers,
    opportunities,
    service_categories,
    source_records,
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
router.include_router(follow_ups.router, prefix="/follow-ups", tags=["follow-ups"])
router.include_router(compliance_events.router, prefix="/compliance-events", tags=["compliance-events"])
router.include_router(external_sources.router, prefix="/external-sources", tags=["external-sources"])
router.include_router(source_records.router, prefix="/source-records", tags=["source-records"])
