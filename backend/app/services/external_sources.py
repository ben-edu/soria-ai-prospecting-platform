"""External opportunity source providers and service layer.

Phase 9A — External Opportunity Sources Foundation.

All providers are deterministic mocks. No real external API calls.
"""

from datetime import datetime, timezone
from typing import Optional

from app.schemas.external_source import (
    ExternalOpportunityCandidate,
    ExternalSourceProviderInfo,
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


def list_external_source_providers() -> list[ExternalSourceProviderInfo]:
    """Return info for every registered external source provider."""
    return [
        cls.get_provider_info()
        for cls in PROVIDER_REGISTRY.values()
    ]


def get_external_source_provider(provider_name: str) -> "BaseExternalSourceProvider":
    """Resolve and return an external source provider instance by name.

    Raises ValueError if the provider name is not registered.
    """
    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(
            f"Unknown external source provider: '{provider_name}'. "
            f"Available providers: [{available}]"
        )
    return PROVIDER_REGISTRY[provider_name]()


def search_external_opportunities(
    provider_name: str,
    query: str,
    location: Optional[str] = None,
    limit: int = 10,
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

    Returns
    -------
    List of matching opportunity candidates.

    Raises
    ------
    ValueError
        If *provider_name* is not registered.
    """
    provider = get_external_source_provider(provider_name)
    return provider.search(query=query, location=location, limit=limit)


def search_multiple_external_sources(
    providers: list[str],
    query: str,
    location: Optional[str] = None,
    limit: int = 10,
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

    @classmethod
    def get_provider_info(cls) -> ExternalSourceProviderInfo:
        return ExternalSourceProviderInfo(
            provider=cls.provider,
            label=cls.label,
            country=cls.country,
            source_kind=cls.source_kind,
            is_enabled=cls.is_enabled,
            is_mock=cls.is_mock,
            requires_credentials=cls.requires_credentials,
            description=cls.description,
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
