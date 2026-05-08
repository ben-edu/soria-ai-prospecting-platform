"""Pydantic schemas for external opportunity sources.

Phase 9A — External Opportunity Sources Foundation.
Phase 9B — Import External Candidate into SourceRecord + Company + Opportunity.
Phase 10A — Real External API Configuration Foundation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ExternalSourceProviderInfo(BaseModel):
    """Information about a single external source provider.

    Phase 10A adds diagnostics fields for real API configuration:
    - supports_real_api: whether a real API connector is planned
    - credentials_configured: whether required credentials are set in env
    - real_api_enabled: whether real API mode is active
    - safe_status / safe_message: human-readable safety summary
    """

    provider: str
    label: str
    country: Optional[str] = None
    source_kind: str
    is_enabled: bool
    is_mock: bool
    requires_credentials: bool
    description: str

    # Phase 10A — real API configuration diagnostics
    supports_real_api: bool = False
    credentials_configured: bool = False
    real_api_enabled: bool = False
    safe_status: str = "mock"
    safe_message: str = ""


class ExternalOpportunityCandidate(BaseModel):
    """A single opportunity candidate from an external source.

    Phase 9B will map this to SourceRecord, Company, and Opportunity.
    """

    provider: str
    external_id: str
    source_kind: str
    title: str
    company_name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    language: str
    source_url: Optional[str] = None
    source_published_at: Optional[datetime] = None
    contract_type: Optional[str] = None
    remote_type: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    budget_currency: Optional[str] = None
    tags: list[str] = []
    raw_payload: dict = {}


class ExternalOpportunitySearchResponse(BaseModel):
    """Response from an external opportunity search."""

    provider: Optional[str] = None
    query: str
    location: Optional[str] = None
    total: int
    items: list[ExternalOpportunityCandidate]


class ExternalSourceDiagnosticsResponse(BaseModel):
    """Diagnostics response listing available external source providers.

    Phase 10A adds *mode* to reflect the current EXTERNAL_SOURCES_MODE setting.
    """

    providers: list[ExternalSourceProviderInfo]
    enabled_providers: list[str]
    mock_only: bool
    mode: str = "mock"
    message: str


class ImportExternalCandidateResponse(BaseModel):
    """Response from importing an external candidate.

    Phase 9B — returns created/reused SourceRecord, Company, Opportunity.
    """

    source_record: dict = {}
    company: dict = {}
    opportunity: dict = {}
    created_source_record: bool
    created_company: bool
    created_opportunity: bool
    duplicate_detected: bool
    message: str
