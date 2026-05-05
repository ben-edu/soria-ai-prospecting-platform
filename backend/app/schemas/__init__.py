from app.schemas.academy_resource import (
    AcademyResourceCreate,
    AcademyResourceListResponse,
    AcademyResourceRead,
    AcademyResourceUpdate,
)
from app.schemas.common import Message, PaginatedResponse, TimestampMixin, UUIDMixin
from app.schemas.company import CompanyCreate, CompanyListResponse, CompanyRead, CompanyUpdate
from app.schemas.contact import ContactCreate, ContactListResponse, ContactRead, ContactUpdate
from app.schemas.message_draft import MessageDraftCreate, MessageDraftListResponse, MessageDraftRead, MessageDraftUpdate
from app.schemas.offer import OfferCreate, OfferListResponse, OfferRead, OfferUpdate
from app.schemas.opportunity import (
    EnrichResponse,
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityRead,
    OpportunityUpdate,
    ScoreResponse,
)

__all__ = [
    "Message",
    "PaginatedResponse",
    "TimestampMixin",
    "UUIDMixin",
    "CompanyCreate",
    "CompanyRead",
    "CompanyUpdate",
    "CompanyListResponse",
    "ContactCreate",
    "ContactRead",
    "ContactUpdate",
    "ContactListResponse",
    "OpportunityCreate",
    "OpportunityRead",
    "OpportunityUpdate",
    "OpportunityListResponse",
    "ScoreResponse",
    "EnrichResponse",
    "OfferCreate",
    "OfferRead",
    "OfferUpdate",
    "OfferListResponse",
    "AcademyResourceCreate",
    "AcademyResourceRead",
    "AcademyResourceUpdate",
    "AcademyResourceListResponse",
    "MessageDraftCreate",
    "MessageDraftRead",
    "MessageDraftUpdate",
    "MessageDraftListResponse",
]
