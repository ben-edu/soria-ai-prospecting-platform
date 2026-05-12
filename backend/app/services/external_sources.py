"""External opportunity source providers and service layer.

Phase 9A — External Opportunity Sources Foundation.
Phase 10A — Real External API Configuration Foundation (diagnostics + settings).

All providers are deterministic mocks. No real external API calls.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.core.config import Settings
from app.core.enums import (
    CompanyStatus,
    OpportunityPriority,
    OpportunityStatus,
    OpportunityType,
    SourceType,
)
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.source_record import SourceRecord
from app.schemas.external_source import (
    ExternalOpportunityCandidate,
    ExternalSourceProviderInfo,
    ImportExternalCandidateResponse,
)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, type["BaseExternalSourceProvider"]] = {}


def register_external_source(name: str):
    """Decorator to register an external source provider class."""
    def wrapper(cls):
        PROVIDER_REGISTRY[name] = cls
        return cls
    return wrapper


def list_external_source_providers(
    settings: Optional[Settings] = None,
) -> list[ExternalSourceProviderInfo]:
    """Return info for every registered external source provider.

    Parameters
    ----------
    settings
        Optional Settings instance. When provided, diagnostics fields
        (*credentials_configured*, *real_api_enabled*, *safe_status*,
        *safe_message*) are computed from the current configuration.
    """
    return [
        cls.get_provider_info(settings=settings)
        for cls in PROVIDER_REGISTRY.values()
    ]


def get_external_source_provider(
    provider_name: str,
    settings: Optional[Settings] = None,
) -> "BaseExternalSourceProvider":
    """Resolve and return an external source provider instance by name.

    Parameters
    ----------
    provider_name
        Registered provider name.
    settings
        Optional Settings instance for real API configuration.
        Passed to the provider constructor for live-mode routing.

    Raises ValueError if the provider name is not registered.
    """
    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(
            f"Unknown external source provider: '{provider_name}'. "
            f"Available providers: [{available}]"
        )
    return PROVIDER_REGISTRY[provider_name](settings=settings)


def search_external_opportunities(
    provider_name: str,
    query: str,
    location: Optional[str] = None,
    limit: int = 10,
    settings: Optional[Settings] = None,
) -> list[ExternalOpportunityCandidate]:
    """Search a single external source provider for opportunities.

    Parameters
    ----------
    provider_name
        Registered provider name.
    query
        Free-text search query (required, must not be blank).
    location
        Optional location filter.
    limit
        Maximum number of results (1-50).
    settings
        Optional Settings instance for live-mode routing.

    Returns
    -------
    List of matching opportunity candidates.

    Raises
    ------
    ValueError
        If *provider_name* is not registered, or if a live provider
        raises a controlled error.
    """
    provider = get_external_source_provider(provider_name, settings=settings)
    return provider.search(query=query, location=location, limit=limit)


def search_multiple_external_sources(
    providers: list[str],
    query: str,
    location: Optional[str] = None,
    limit: int = 10,
    settings: Optional[Settings] = None,
) -> list[ExternalOpportunityCandidate]:
    """Search across multiple external source providers.

    Parameters
    ----------
    providers
        List of registered provider names.
    query
        Free-text search query.
    location
        Optional location filter.
    limit
        Maximum results *per provider* (total = len(providers) * limit).
    settings
        Optional Settings instance for live-mode routing.

    Returns
    -------
    Flattened list of candidates from all requested providers.
    """
    results: list[ExternalOpportunityCandidate] = []
    for name in providers:
        candidates = search_external_opportunities(
            provider_name=name,
            query=query,
            location=location,
            limit=limit,
            settings=settings,
        )
        results.extend(candidates)
    return results


def get_enabled_provider_names() -> list[str]:
    """Return sorted list of registered provider names (all enabled in Phase 9A)."""
    return sorted(PROVIDER_REGISTRY)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseExternalSourceProvider:
    """Base class for external source providers."""

    provider: str = ""
    label: str = ""
    country: Optional[str] = None
    source_kind: str = ""
    is_enabled: bool = True
    is_mock: bool = True
    requires_credentials: bool = False
    description: str = ""
    language: str = ""

    # Phase 10A — real API configuration
    supports_real_api: bool = False
    _credential_fields: list[str] = []

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings

    @classmethod
    def check_credentials_configured(cls, settings: Settings) -> bool:
        """Return True if all required credential env vars have truthy values."""
        return all(
            getattr(settings, field, None)
            for field in cls._credential_fields
        )

    @classmethod
    def get_provider_info(
        cls,
        settings: Optional[Settings] = None,
    ) -> ExternalSourceProviderInfo:
        credentials_configured = False
        real_api_enabled = False

        if settings is not None and cls.supports_real_api:
            credentials_configured = cls.check_credentials_configured(settings)
            real_api_enabled = (
                settings.EXTERNAL_SOURCES_MODE != "mock"
                and credentials_configured
            )

        # Determine if live mode was requested (even if is_mock is True)
        live_requested = (
            settings is not None
            and settings.EXTERNAL_SOURCES_MODE != "mock"
        ) if cls.supports_real_api else False

        # Compute safe_status / safe_message
        if cls.is_mock:
            if real_api_enabled:
                safe_status = "ready"
                safe_message = "Real API configured and ready."
            elif live_requested and not credentials_configured:
                safe_status = "missing_credentials"
                safe_message = "Real API selected but credentials not configured."
            elif cls.supports_real_api and credentials_configured:
                safe_status = "mock"
                safe_message = (
                    "Mock mode active. Real API credentials configured — "
                    "set EXTERNAL_SOURCES_MODE to enable."
                )
            elif cls.supports_real_api:
                safe_status = "mock"
                safe_message = (
                    "Mock mode active. Real API credentials not configured."
                )
            else:
                safe_status = "mock"
                safe_message = "Mock mode active. No real API available."
        elif not cls.supports_real_api:
            safe_status = "unsupported"
            safe_message = "No real API implementation."
        elif not credentials_configured:
            safe_status = "missing_credentials"
            safe_message = "Real API selected but credentials not configured."
        else:
            safe_status = "ready"
            safe_message = "Real API configured and ready."

        return ExternalSourceProviderInfo(
            provider=cls.provider,
            label=cls.label,
            country=cls.country,
            source_kind=cls.source_kind,
            is_enabled=cls.is_enabled,
            is_mock=cls.is_mock,
            requires_credentials=cls.requires_credentials,
            description=cls.description,
            supports_real_api=cls.supports_real_api,
            credentials_configured=credentials_configured,
            real_api_enabled=real_api_enabled,
            safe_status=safe_status,
            safe_message=safe_message,
        )

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        """Search this provider for matching opportunities.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def _filter_by_query(self, candidates: list[dict], query: str) -> list[dict]:
        """Lightly filter candidates by matching query text against title/description/tags."""
        query_lower = query.strip().lower()
        if not query_lower:
            return candidates

        def _matches(c: dict) -> bool:
            haystack = (
                (c.get("title") or "")
                + " "
                + (c.get("description") or "")
                + " "
                + " ".join(c.get("tags") or [])
            ).lower()
            return query_lower in haystack

        return [c for c in candidates if _matches(c)]


# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


@register_external_source("france_travail")
class FranceTravailMockProvider(BaseExternalSourceProvider):
    """Deterministic mock for France Travail (French job board).

    Returns DevOps, cloud, and training job candidates in France.
    """

    provider = "france_travail"
    label = "France Travail"
    country = "FR"
    source_kind = "job"
    description = "Offres d'emploi via France Travail (Pôle emploi)"
    language = "fr"
    supports_real_api = True
    _credential_fields = ["FRANCE_TRAVAIL_CLIENT_ID", "FRANCE_TRAVAIL_CLIENT_SECRET"]

    _MOCK_CANDIDATES: list[dict] = [
        {
            "external_id": "fr-001",
            "title": "Ingénieur DevOps",
            "company_name": "TechCorp France",
            "description": (
                "Recherche ingénieur DevOps expérimenté pour gérer"
                " l'infrastructure cloud et les pipelines CI/CD."
            ),
            "location": "Paris",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "hybrid",
            "tags": ["devops", "cloud", "ci/cd", "kubernetes"],
        },
        {
            "external_id": "fr-002",
            "title": "Architecte Cloud AWS",
            "company_name": "Cloud Solutions SAS",
            "description": (
                "Conception et déploiement d'architectures cloud AWS"
                " pour nos clients enterprise."
            ),
            "location": "Lyon",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "remote",
            "tags": ["cloud", "aws", "architecture", "devops"],
        },
        {
            "external_id": "fr-003",
            "title": "Formateur DevOps & Cloud",
            "company_name": "SORIA Academy",
            "description": (
                "Animation de formations DevOps, Cloud et Kubernetes"
                " pour des professionnels en reconversion."
            ),
            "location": "Paris",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "hybrid",
            "tags": ["formation", "devops", "cloud", "kubernetes", "training"],
        },
        {
            "external_id": "fr-004",
            "title": "Ingénieur Sécurité Cloud",
            "company_name": "CyberDefense FR",
            "description": (
                "Sécurisation d'infrastructures cloud multi-comptes AWS et Azure."
            ),
            "location": "Toulouse",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "remote",
            "tags": ["security", "cloud", "aws", "azure", "cybersecurity"],
        },
        {
            "external_id": "fr-005",
            "title": "Administrateur Kubernetes",
            "company_name": "Numérix Solutions",
            "description": (
                "Administration de clusters Kubernetes en production"
                " pour une plateforme SaaS."
            ),
            "location": "Bordeaux",
            "country": "FR",
            "contract_type": "CDD",
            "remote_type": "hybrid",
            "tags": ["kubernetes", "devops", "cloud", "saas"],
        },
        {
            "external_id": "fr-006",
            "title": "Chef de Projet Digital Learning",
            "company_name": "Digital Campus",
            "description": (
                "Coordination de projets de formation digitale"
                " et déploiement de parcours e-learning."
            ),
            "location": "Nantes",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "hybrid",
            "tags": ["formation", "digital", "elearning", "project management"],
        },
    ]

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        # Phase 10C — live-mode routing
        settings = self._settings
        if settings is not None and settings.EXTERNAL_SOURCES_MODE != "mock":
            if self.check_credentials_configured(settings):
                try:
                    from app.services.france_travail_client import (
                        FranceTravailAPIClient,
                        FranceTravailClientError,
                    )
                    api_client = FranceTravailAPIClient(settings=settings)
                    return api_client.search_offers(
                        query=query, location=location, limit=limit,
                    )
                except FranceTravailClientError as exc:
                    raise ValueError(
                        f"France Travail search failed: {exc}"
                    )
            # Live mode but credentials missing — safe fallback to mock

        # Default mock behavior (unchanged)
        candidates = self._filter_by_query(self._MOCK_CANDIDATES, query)

        if location:
            loc_lower = location.strip().lower()
            candidates = [
                c for c in candidates
                if loc_lower in (c.get("location") or "").lower()
            ]

        candidates = candidates[:limit]

        return [
            ExternalOpportunityCandidate(
                provider=self.provider,
                external_id=c["external_id"],
                source_kind=self.source_kind,
                title=c["title"],
                company_name=c["company_name"],
                description=c["description"],
                location=c["location"],
                country=self.country,
                language=self.language,
                source_url=None,
                source_published_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
                contract_type=c["contract_type"],
                remote_type=c["remote_type"],
                budget_min=None,
                budget_max=None,
                budget_currency=None,
                tags=c["tags"],
                raw_payload=c.copy(),
            )
            for c in candidates
        ]


@register_external_source("adzuna_uk")
class AdzunaUkMockProvider(BaseExternalSourceProvider):
    """Deterministic mock for Adzuna UK (UK job board).

    Returns DevOps, cloud, and cybersecurity job candidates in the UK.
    """

    provider = "adzuna_uk"
    label = "Adzuna UK"
    country = "GB"
    source_kind = "job"
    description = "UK job listings via Adzuna"
    language = "en"
    supports_real_api = True
    _credential_fields = ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]

    _MOCK_CANDIDATES: list[dict] = [
        {
            "external_id": "uk-001",
            "title": "DevOps Engineer",
            "company_name": "CloudBase Ltd",
            "description": (
                "Join our platform team to build and maintain CI/CD pipelines"
                " and Kubernetes infrastructure."
            ),
            "location": "London",
            "country": "GB",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["devops", "kubernetes", "ci/cd", "terraform"],
        },
        {
            "external_id": "uk-002",
            "title": "Cloud Solutions Architect",
            "company_name": "TechInnovate UK",
            "description": (
                "Design and implement scalable cloud solutions"
                " on AWS and Azure for enterprise clients."
            ),
            "location": "Manchester",
            "country": "GB",
            "contract_type": "permanent",
            "remote_type": "remote",
            "tags": ["cloud", "aws", "azure", "architecture"],
        },
        {
            "external_id": "uk-003",
            "title": "Cyber Security Analyst",
            "company_name": "SecureNet UK",
            "description": (
                "Monitor and respond to security incidents,"
                " conduct penetration testing and vulnerability assessments."
            ),
            "location": "Birmingham",
            "country": "GB",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["cybersecurity", "security", "penetration testing", "soc"],
        },
        {
            "external_id": "uk-004",
            "title": "Senior DevOps Engineer",
            "company_name": "FinTech Solutions UK",
            "description": (
                "Lead DevOps practices in a fast-paced fintech environment"
                " with multi-cloud infrastructure."
            ),
            "location": "Edinburgh",
            "country": "GB",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["devops", "fintech", "cloud", "kubernetes", "ci/cd"],
        },
        {
            "external_id": "uk-005",
            "title": "Cloud Security Engineer",
            "company_name": "DataGuard UK",
            "description": (
                "Implement security controls for cloud infrastructure"
                " and ensure compliance with UK standards."
            ),
            "location": "London",
            "country": "GB",
            "contract_type": "contract",
            "remote_type": "remote",
            "tags": ["security", "cloud", "compliance", "aws"],
        },
        {
            "external_id": "uk-006",
            "title": "IT Trainer — Cloud & DevOps",
            "company_name": "SkillsForge UK",
            "description": (
                "Deliver training programmes on cloud computing,"
                " DevOps practices, and infrastructure automation."
            ),
            "location": "Bristol",
            "country": "GB",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["training", "cloud", "devops", "education"],
        },
    ]

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        # Phase 10E — live-mode routing
        settings = self._settings
        if settings is not None and settings.EXTERNAL_SOURCES_MODE != "mock":
            if self.check_credentials_configured(settings):
                try:
                    from app.services.adzuna_uk_client import (
                        AdzunaUKAPIClient,
                        AdzunaUKClientError,
                    )
                    api_client = AdzunaUKAPIClient(settings=settings)
                    return api_client.search_jobs(
                        query=query, location=location, limit=limit,
                    )
                except AdzunaUKClientError as exc:
                    raise ValueError(
                        f"Adzuna UK search failed: {exc}"
                    )
            # Live mode but credentials missing — safe fallback to mock

        # Default mock behavior (unchanged)
        candidates = self._filter_by_query(self._MOCK_CANDIDATES, query)

        if location:
            loc_lower = location.strip().lower()
            candidates = [
                c for c in candidates
                if loc_lower in (c.get("location") or "").lower()
            ]

        candidates = candidates[:limit]

        return [
            ExternalOpportunityCandidate(
                provider=self.provider,
                external_id=c["external_id"],
                source_kind=self.source_kind,
                title=c["title"],
                company_name=c["company_name"],
                description=c["description"],
                location=c["location"],
                country=self.country,
                language=self.language,
                source_url=None,
                source_published_at=datetime(2025, 7, 1, tzinfo=timezone.utc),
                contract_type=c["contract_type"],
                remote_type=c["remote_type"],
                budget_min=None,
                budget_max=None,
                budget_currency=None,
                tags=c["tags"],
                raw_payload=c.copy(),
            )
            for c in candidates
        ]


@register_external_source("adzuna_fr")
class AdzunaFrMockProvider(BaseExternalSourceProvider):
    """Deterministic mock for Adzuna France (French job board).

    Returns DevOps, cloud, and infrastructure job candidates in France.
    """

    provider = "adzuna_fr"
    label = "Adzuna France"
    country = "FR"
    source_kind = "job"
    description = "Offres d'emploi via Adzuna France"
    language = "fr"
    supports_real_api = True
    _credential_fields = ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]

    _MOCK_CANDIDATES: list[dict] = [
        {
            "external_id": "adz-fr-001",
            "title": "Ingénieur DevOps",
            "company_name": "CloudBase France SAS",
            "description": (
                "Rejoignez notre équipe plateforme pour construire et maintenir"
                " des pipelines CI/CD et une infrastructure Kubernetes."
            ),
            "location": "Paris",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "hybrid",
            "tags": ["devops", "kubernetes", "ci/cd", "terraform"],
        },
        {
            "external_id": "adz-fr-002",
            "title": "Architecte Cloud AWS",
            "company_name": "TechInnovate France",
            "description": (
                "Concevoir et déployer des solutions cloud évolutives"
                " sur AWS et Azure pour des clients enterprise."
            ),
            "location": "Lyon",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "remote",
            "tags": ["cloud", "aws", "azure", "architecture"],
        },
        {
            "external_id": "adz-fr-003",
            "title": "Administrateur Kubernetes",
            "company_name": "Numérix Solutions",
            "description": (
                "Administration de clusters Kubernetes en production"
                " pour une plateforme SaaS à grande échelle."
            ),
            "location": "Bordeaux",
            "country": "FR",
            "contract_type": "CDD",
            "remote_type": "hybrid",
            "tags": ["kubernetes", "devops", "cloud", "saas"],
        },
        {
            "external_id": "adz-fr-004",
            "title": "Ingénieur Sécurité Cloud",
            "company_name": "CyberDefense FR",
            "description": (
                "Sécurisation d'infrastructures cloud multi-comptes"
                " et mise en place de politiques de conformité."
            ),
            "location": "Toulouse",
            "country": "FR",
            "contract_type": "CDI",
            "remote_type": "remote",
            "tags": ["security", "cloud", "cybersecurity", "compliance"],
        },
    ]

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        # Phase 12C — live-mode routing to AdzunaUKAPIClient with country_code="fr"
        settings = self._settings
        if settings is not None and settings.EXTERNAL_SOURCES_MODE != "mock":
            if self.check_credentials_configured(settings):
                try:
                    from app.services.adzuna_uk_client import (
                        AdzunaUKAPIClient,
                        AdzunaUKClientError,
                    )
                    api_client = AdzunaUKAPIClient(
                        settings=settings, country_code="fr"
                    )
                    return api_client.search_jobs(
                        query=query, location=location, limit=limit,
                    )
                except AdzunaUKClientError as exc:
                    raise ValueError(
                        f"Adzuna France search failed: {exc}"
                    )
            # Live mode but credentials missing — safe fallback to mock

        # Default mock behavior (unchanged)
        candidates = self._filter_by_query(self._MOCK_CANDIDATES, query)

        if location:
            loc_lower = location.strip().lower()
            candidates = [
                c for c in candidates
                if loc_lower in (c.get("location") or "").lower()
            ]

        candidates = candidates[:limit]

        return [
            ExternalOpportunityCandidate(
                provider=self.provider,
                external_id=c["external_id"],
                source_kind=self.source_kind,
                title=c["title"],
                company_name=c["company_name"],
                description=c["description"],
                location=c["location"],
                country=self.country,
                language=self.language,
                source_url=None,
                source_published_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
                contract_type=c["contract_type"],
                remote_type=c["remote_type"],
                budget_min=None,
                budget_max=None,
                budget_currency=None,
                tags=c["tags"],
                raw_payload=c.copy(),
            )
            for c in candidates
        ]


@register_external_source("adzuna_de")
class AdzunaDeMockProvider(BaseExternalSourceProvider):
    """Deterministic mock for Adzuna Germany (German job board).

    Returns DevOps, cloud, and infrastructure job candidates in Germany.
    """

    provider = "adzuna_de"
    label = "Adzuna Germany"
    country = "DE"
    source_kind = "job"
    description = "Jobangebote über Adzuna Deutschland"
    language = "de"
    supports_real_api = True
    _credential_fields = ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]

    _MOCK_CANDIDATES: list[dict] = [
        {
            "external_id": "adz-de-001",
            "title": "DevOps Engineer",
            "company_name": "CloudBase GmbH",
            "description": (
                "Werden Sie Teil unseres Plattform-Teams und bauen Sie"
                " CI/CD-Pipelines und Kubernetes-Infrastruktur auf."
            ),
            "location": "Berlin",
            "country": "DE",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["devops", "kubernetes", "ci/cd", "terraform"],
        },
        {
            "external_id": "adz-de-002",
            "title": "Cloud Solutions Architect",
            "company_name": "TechInnovate Deutschland",
            "description": (
                "Entwerfen und implementieren Sie skalierbare Cloud-Lösungen"
                " auf AWS und Azure für Unternehmenskunden."
            ),
            "location": "München",
            "country": "DE",
            "contract_type": "permanent",
            "remote_type": "remote",
            "tags": ["cloud", "aws", "azure", "architecture"],
        },
        {
            "external_id": "adz-de-003",
            "title": "Kubernetes Administrator",
            "company_name": "Numérix Solutions GmbH",
            "description": (
                "Administration von Kubernetes-Clustern in der Produktion"
                " für eine große SaaS-Plattform."
            ),
            "location": "Hamburg",
            "country": "DE",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["kubernetes", "devops", "cloud", "saas"],
        },
        {
            "external_id": "adz-de-004",
            "title": "Cloud Security Engineer",
            "company_name": "CyberDefense GmbH",
            "description": (
                "Sicherung von Multi-Cloud-Infrastrukturen"
                " und Implementierung von Compliance-Richtlinien."
            ),
            "location": "Frankfurt",
            "country": "DE",
            "contract_type": "permanent",
            "remote_type": "remote",
            "tags": ["security", "cloud", "cybersecurity", "compliance"],
        },
    ]

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        # Phase 12C — live-mode routing to AdzunaUKAPIClient with country_code="de"
        settings = self._settings
        if settings is not None and settings.EXTERNAL_SOURCES_MODE != "mock":
            if self.check_credentials_configured(settings):
                try:
                    from app.services.adzuna_uk_client import (
                        AdzunaUKAPIClient,
                        AdzunaUKClientError,
                    )
                    api_client = AdzunaUKAPIClient(
                        settings=settings, country_code="de"
                    )
                    return api_client.search_jobs(
                        query=query, location=location, limit=limit,
                    )
                except AdzunaUKClientError as exc:
                    raise ValueError(
                        f"Adzuna Germany search failed: {exc}"
                    )
            # Live mode but credentials missing — safe fallback to mock

        # Default mock behavior (unchanged)
        candidates = self._filter_by_query(self._MOCK_CANDIDATES, query)

        if location:
            loc_lower = location.strip().lower()
            candidates = [
                c for c in candidates
                if loc_lower in (c.get("location") or "").lower()
            ]

        candidates = candidates[:limit]

        return [
            ExternalOpportunityCandidate(
                provider=self.provider,
                external_id=c["external_id"],
                source_kind=self.source_kind,
                title=c["title"],
                company_name=c["company_name"],
                description=c["description"],
                location=c["location"],
                country=self.country,
                language=self.language,
                source_url=None,
                source_published_at=datetime(2025, 9, 15, tzinfo=timezone.utc),
                contract_type=c["contract_type"],
                remote_type=c["remote_type"],
                budget_min=None,
                budget_max=None,
                budget_currency=None,
                tags=c["tags"],
                raw_payload=c.copy(),
            )
            for c in candidates
        ]


@register_external_source("freelancer")
class FreelancerMockProvider(BaseExternalSourceProvider):
    """Deterministic mock for Freelancer.com (global freelance marketplace).

    Returns freelance DevOps, cloud, and security project candidates.
    """

    provider = "freelancer"
    label = "Freelancer.com"
    country = "GLOBAL"
    source_kind = "freelance_project"
    description = "Freelance project opportunities from Freelancer.com"
    language = "en"
    supports_real_api = True
    _credential_fields = ["FREELANCER_OAUTH_TOKEN"]

    _MOCK_CANDIDATES: list[dict] = [
        {
            "external_id": "fl-001",
            "title": "Kubernetes Cluster Setup and Migration",
            "company_name": "GlobalTech GmbH",
            "description": (
                "Need an experienced freelancer to set up a production-grade"
                " Kubernetes cluster and migrate existing workloads."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "project",
            "remote_type": "remote",
            "budget_min": 3000.0,
            "budget_max": 8000.0,
            "budget_currency": "EUR",
            "tags": ["kubernetes", "devops", "migration", "cloud"],
        },
        {
            "external_id": "fl-002",
            "title": "AWS Infrastructure Automation",
            "company_name": "StartupHub Inc",
            "description": (
                "Design and implement Terraform modules"
                " for a multi-account AWS setup with CI/CD pipelines."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "project",
            "remote_type": "remote",
            "budget_min": 2500.0,
            "budget_max": 6000.0,
            "budget_currency": "USD",
            "tags": ["aws", "terraform", "devops", "automation", "ci/cd"],
        },
        {
            "external_id": "fl-003",
            "title": "Security Audit and Hardening",
            "company_name": "SecureStart Ltd",
            "description": (
                "Conduct a full security audit of cloud infrastructure"
                " and provide hardening recommendations and implementation."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "project",
            "remote_type": "remote",
            "budget_min": 2000.0,
            "budget_max": 5000.0,
            "budget_currency": "USD",
            "tags": ["security", "audit", "hardening", "cloud"],
        },
        {
            "external_id": "fl-004",
            "title": "DevOps CI/CD Pipeline Setup",
            "company_name": "AppDev Studios",
            "description": (
                "Set up complete CI/CD pipeline with GitHub Actions,"
                " Docker, and automated testing for a web application."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "project",
            "remote_type": "remote",
            "budget_min": 1500.0,
            "budget_max": 4000.0,
            "budget_currency": "USD",
            "tags": ["devops", "ci/cd", "github actions", "docker"],
        },
        {
            "external_id": "fl-005",
            "title": "Cloud Training Material Development",
            "company_name": "EduCloud International",
            "description": (
                "Develop comprehensive training materials"
                " for cloud computing certification courses (AWS/Azure/GCP)."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "project",
            "remote_type": "remote",
            "budget_min": 4000.0,
            "budget_max": 10000.0,
            "budget_currency": "EUR",
            "tags": ["training", "cloud", "aws", "azure", "education", "content"],
        },
        {
            "external_id": "fl-006",
            "title": "Platform Engineering Consulting",
            "company_name": "ScaleUp Technologies",
            "description": (
                "Short-term consulting engagement to design"
                " a platform engineering strategy and internal developer platform."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "project",
            "remote_type": "remote",
            "budget_min": 5000.0,
            "budget_max": 15000.0,
            "budget_currency": "USD",
            "tags": ["platform engineering", "devops", "consulting", "cloud"],
        },
    ]

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        # Phase 10F — live-mode routing for Freelancer real connector
        settings = self._settings
        if settings is not None and settings.EXTERNAL_SOURCES_MODE != "mock":
            if self.check_credentials_configured(settings):
                try:
                    from app.services.freelancer_client import (
                        FreelancerAPIClient,
                        FreelancerClientError,
                    )
                    api_client = FreelancerAPIClient(settings=settings)
                    return api_client.search_projects(
                        query=query, location=location, limit=limit,
                    )
                except FreelancerClientError as exc:
                    raise ValueError(
                        f"Freelancer search failed: {exc}"
                    )
            # Live mode but credentials missing — safe fallback to mock

        candidates = self._filter_by_query(self._MOCK_CANDIDATES, query)

        if location:
            loc_lower = location.strip().lower()
            candidates = [
                c for c in candidates
                if loc_lower in (c.get("location") or "").lower()
                or loc_lower in (c.get("country") or "").lower()
            ]

        candidates = candidates[:limit]

        return [
            ExternalOpportunityCandidate(
                provider=self.provider,
                external_id=c["external_id"],
                source_kind=self.source_kind,
                title=c["title"],
                company_name=c["company_name"],
                description=c["description"],
                location=c["location"],
                country=self.country,
                language=self.language,
                source_url=None,
                source_published_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
                contract_type=c["contract_type"],
                remote_type=c["remote_type"],
                budget_min=c["budget_min"],
                budget_max=c["budget_max"],
                budget_currency=c["budget_currency"],
                tags=c["tags"],
                raw_payload=c.copy(),
            )
            for c in candidates
        ]


@register_external_source("jooble")
class JoobleMockProvider(BaseExternalSourceProvider):
    """Deterministic mock for Jooble (global job search engine).

    Returns DevOps, cloud, and infrastructure job candidates globally.
    """

    provider = "jooble"
    label = "Jooble"
    country = "GLOBAL"
    source_kind = "job"
    description = "Global job listings via Jooble"
    language = "en"
    supports_real_api = True
    _credential_fields = ["JOOBLE_API_KEY"]

    _MOCK_CANDIDATES: list[dict] = [
        {
            "external_id": "job-gl-001",
            "title": "Senior DevOps Engineer",
            "company_name": "GlobalTech Inc.",
            "description": (
                "Build and maintain large-scale CI/CD pipelines and"
                " Kubernetes infrastructure for a global SaaS platform."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "full-time",
            "remote_type": "remote",
            "tags": ["devops", "kubernetes", "ci/cd", "terraform"],
        },
        {
            "external_id": "job-gl-002",
            "title": "Cloud Architect",
            "company_name": "CloudScale GmbH",
            "description": (
                "Design multi-cloud architectures on AWS, Azure, and GCP"
                " for enterprise customers worldwide."
            ),
            "location": "Berlin",
            "country": "DE",
            "contract_type": "full-time",
            "remote_type": "hybrid",
            "tags": ["cloud", "aws", "azure", "gcp", "architecture"],
        },
        {
            "external_id": "job-gl-003",
            "title": "Platform Engineer",
            "company_name": "DataStream Ltd",
            "description": (
                "Develop and operate the internal developer platform"
                " powering our data infrastructure team."
            ),
            "location": "London",
            "country": "GB",
            "contract_type": "permanent",
            "remote_type": "hybrid",
            "tags": ["platform engineering", "devops", "kubernetes", "cloud"],
        },
        {
            "external_id": "job-gl-004",
            "title": "DevSecOps Engineer",
            "company_name": "SecurePath Inc.",
            "description": (
                "Integrate security practices into CI/CD pipelines"
                " and automate compliance validation for cloud deployments."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "contract",
            "remote_type": "remote",
            "tags": ["devsecops", "security", "ci/cd", "automation"],
        },
        {
            "external_id": "job-gl-005",
            "title": "Infrastructure Automation Lead",
            "company_name": "BuildRight Corp",
            "description": (
                "Lead the infrastructure automation team to deliver"
                " IaC solutions using Terraform and Ansible."
            ),
            "location": "New York",
            "country": "US",
            "contract_type": "full-time",
            "remote_type": "hybrid",
            "tags": ["infrastructure", "automation", "terraform", "ansible"],
        },
        {
            "external_id": "job-gl-006",
            "title": "Cloud Training Specialist",
            "company_name": "EduCloud Global",
            "description": (
                "Create and deliver technical training programs"
                " on cloud computing and DevOps practices."
            ),
            "location": "Remote",
            "country": "GLOBAL",
            "contract_type": "contract",
            "remote_type": "remote",
            "tags": ["training", "cloud", "devops", "education"],
        },
    ]

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[ExternalOpportunityCandidate]:
        # Phase 12D — live-mode routing
        settings = self._settings
        if settings is not None and settings.EXTERNAL_SOURCES_MODE != "mock":
            if self.check_credentials_configured(settings):
                try:
                    from app.services.jooble_client import (
                        JoobleAPIClient,
                        JoobleClientError,
                    )
                    api_client = JoobleAPIClient(settings=settings)
                    return api_client.search_jobs(
                        query=query, location=location, limit=limit,
                    )
                except JoobleClientError as exc:
                    raise ValueError(
                        f"Jooble search failed: {exc}"
                    )
            # Live mode but credentials missing — safe fallback to mock

        # Default mock behavior (unchanged)
        candidates = self._filter_by_query(self._MOCK_CANDIDATES, query)

        if location:
            loc_lower = location.strip().lower()
            candidates = [
                c for c in candidates
                if loc_lower in (c.get("location") or "").lower()
                or loc_lower in (c.get("country") or "").lower()
            ]

        candidates = candidates[:limit]

        return [
            ExternalOpportunityCandidate(
                provider=self.provider,
                external_id=c["external_id"],
                source_kind=self.source_kind,
                title=c["title"],
                company_name=c["company_name"],
                description=c["description"],
                location=c["location"],
                country=c.get("country") or self.country,
                language=self.language,
                source_url=None,
                source_published_at=datetime(2025, 10, 1, tzinfo=timezone.utc),
                contract_type=c["contract_type"],
                remote_type=c["remote_type"],
                budget_min=None,
                budget_max=None,
                budget_currency=None,
                tags=c["tags"],
                raw_payload=c.copy(),
            )
            for c in candidates
        ]


# ---------------------------------------------------------------------------
# Phase 9B — Import external candidate into SourceRecord + Company + Opportunity
# ---------------------------------------------------------------------------

_DEVOPS_CLOUD_KEYWORDS = {
    "devops", "cloud", "kubernetes", "terraform", "aws", "azure",
    "ci/cd", "ci cd", "docker", "automation", "platform engineering",
    "migration", "infrastructure", "github actions",
}


def _determine_opportunity_type(candidate: ExternalOpportunityCandidate) -> OpportunityType:
    """Determine OpportunityType based on candidate source_kind and content."""
    text_to_check = (
        (candidate.title or "").lower()
        + " "
        + (candidate.description or "").lower()
        + " "
        + " ".join(t.lower() for t in candidate.tags)
    )
    has_devops_cloud = any(kw in text_to_check for kw in _DEVOPS_CLOUD_KEYWORDS)
    if has_devops_cloud:
        return OpportunityType.devops_cloud
    return OpportunityType.other


def _build_opportunity_notes(candidate: ExternalOpportunityCandidate) -> str:
    """Build provenance notes for the Opportunity."""
    lines = [
        f"provider={candidate.provider}",
        f"external_id={candidate.external_id}",
        f"source_kind={candidate.source_kind}",
    ]
    if candidate.country:
        lines.append(f"country={candidate.country}")
    if candidate.contract_type:
        lines.append(f"contract_type={candidate.contract_type}")
    if candidate.remote_type:
        lines.append(f"remote_type={candidate.remote_type}")
    if candidate.budget_min is not None:
        curr = candidate.budget_currency or ""
        lines.append(f"budget_min={candidate.budget_min} {curr}".strip())
    if candidate.budget_max is not None:
        curr = candidate.budget_currency or ""
        lines.append(f"budget_max={candidate.budget_max} {curr}".strip())
    return "\n".join(lines)


def _get_or_create_company(
    candidate: ExternalOpportunityCandidate,
    db: Session,
) -> tuple[Company, bool]:
    """Find existing company by name + country, or create a new one.

    Returns (company, created) where *created* is True if a new Company
    was created.
    """
    company_name = candidate.company_name or f"Unknown External Company - {candidate.provider}"
    country = candidate.country or "France"

    existing = db.query(Company).filter(
        Company.name == company_name,
        Company.country == country,
    ).first()
    if existing:
        return existing, False

    company = Company(
        name=company_name,
        country=country,
        city=candidate.location,
        source=SourceType.france_travail if candidate.provider == "france_travail" else SourceType.other,
        source_url=candidate.source_url,
        status=CompanyStatus.new,
        notes=f"Imported from {candidate.provider}. External ID: {candidate.external_id}",
    )
    db.add(company)
    db.flush()
    db.refresh(company)
    return company, True


def _create_opportunity(
    candidate: ExternalOpportunityCandidate,
    company: Company,
    db: Session,
) -> Opportunity:
    """Create an Opportunity from a candidate."""
    source = (
        SourceType.france_travail
        if candidate.provider == "france_travail"
        else SourceType.other
    )
    default_language = "fr" if candidate.provider == "france_travail" else "en"
    language = candidate.language or default_language

    opportunity = Opportunity(
        company_id=company.id,
        title=candidate.title,
        opportunity_type=_determine_opportunity_type(candidate),
        description=candidate.description,
        source=source,
        source_url=candidate.source_url,
        source_published_at=candidate.source_published_at,
        location=candidate.location,
        language=language,
        status=OpportunityStatus.imported_pending_review,
        priority=OpportunityPriority.medium,
        notes=_build_opportunity_notes(candidate),
    )
    db.add(opportunity)
    db.flush()
    db.refresh(opportunity)
    return opportunity


def import_external_candidate(
    candidate: ExternalOpportunityCandidate,
    db: Session,
) -> ImportExternalCandidateResponse:
    """Import an external opportunity candidate into SORIA.

    Validates the provider, deduplicates by SourceRecord, creates or reuses
    Company and Opportunity, and records the import in a SourceRecord.

    Returns
    -------
    ImportExternalCandidateResponse with the resulting records and flags.

    Raises
    ------
    ValueError
        If *candidate.provider* is not registered.
    """
    # 1. Validate provider exists
    if candidate.provider not in PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown external source provider: '{candidate.provider}'. "
            f"Available providers: [{', '.join(sorted(PROVIDER_REGISTRY))}]"
        )

    # 2. Deduplicate by SourceRecord
    existing_sr = db.query(SourceRecord).filter(
        SourceRecord.source_name == candidate.provider,
        SourceRecord.external_id == candidate.external_id,
    ).first()

    if existing_sr and existing_sr.processed:
        opportunity = db.query(Opportunity).filter(
            Opportunity.notes.contains(f"provider={candidate.provider}"),
            Opportunity.notes.contains(f"external_id={candidate.external_id}"),
        ).first()
        if opportunity:
            company = db.get(Company, opportunity.company_id)
            return ImportExternalCandidateResponse(
                source_record=_dump(existing_sr),
                company=_dump(company),
                opportunity=_dump(opportunity),
                created_source_record=False,
                created_company=False,
                created_opportunity=False,
                duplicate_detected=True,
                message=(
                    f"Duplicate import. Existing SourceRecord "
                    f"({existing_sr.id}) and Opportunity ({opportunity.id}) "
                    f"already exist for provider={candidate.provider} "
                    f"external_id={candidate.external_id}."
                ),
            )

    # 3. Get or create Company
    company, company_created = _get_or_create_company(candidate, db)

    # 4. Create Opportunity
    opportunity = _create_opportunity(candidate, company, db)

    # 5. Create or update SourceRecord
    if existing_sr:
        source_record = existing_sr
        source_record.processed = True
        source_record.processing_notes = (
            f"Company {company.id} ({'created' if company_created else 'reused'}), "
            f"Opportunity {opportunity.id} (created)"
        )
        created_sr = False
    else:
        source_type = (
            SourceType.france_travail
            if candidate.provider == "france_travail"
            else SourceType.other
        )
        source_record = SourceRecord(
            source_type=source_type,
            source_name=candidate.provider,
            source_url=candidate.source_url,
            external_id=candidate.external_id,
            raw_payload=candidate.raw_payload or {},
            imported_at=datetime.now(timezone.utc),
            processed=True,
            processing_notes=(
                f"Company {company.id} ({'created' if company_created else 'reused'}), "
                f"Opportunity {opportunity.id} (created)"
            ),
        )
        db.add(source_record)
        created_sr = True

    db.commit()
    db.refresh(company)
    db.refresh(opportunity)
    db.refresh(source_record)

    return ImportExternalCandidateResponse(
        source_record=_dump(source_record),
        company=_dump(company),
        opportunity=_dump(opportunity),
        created_source_record=created_sr,
        created_company=company_created,
        created_opportunity=True,
        duplicate_detected=False,
        message=(
            f"Import successful. "
            f"SourceRecord ({'created' if created_sr else 'reused'}): {source_record.id}, "
            f"Company ({'created' if company_created else 'reused'}): {company.id}, "
            f"Opportunity (created): {opportunity.id}."
        ),
    )


def _dump(instance) -> dict:
    """Serialize a SQLModel instance to a JSON-safe dict."""
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(instance.model_dump())
