"""Static source catalog — read-only directory of French freelance platforms.

Phase 12B — French Freelance Source Catalog.

This module provides a static catalog of French freelance platforms for
informational/reference purposes only. These entries are NOT registered as
external source providers and CANNOT be searched or imported.

Safety constraints apply uniformly to all catalog entries:
- is_manual_source = True (human-driven, no automation)
- supports_real_api = False (no API integration exists)
- requires_credentials = False (no credentials stored)
- human_review_required = True (human oversight mandatory)
- importable = False (cannot import into SORIA)
- scraping_allowed = False (no scraping)
- external_message_allowed = False (no automated outreach)
"""

from app.schemas.external_source import ExternalSourceCatalogEntry

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

SOURCE_CATALOG: dict[str, ExternalSourceCatalogEntry] = {}

# Shared safety values for all entries
_SAFE = dict(
    is_manual_source=True,
    supports_real_api=False,
    requires_credentials=False,
    human_review_required=True,
    importable=False,
    scraping_allowed=False,
    external_message_allowed=False,
)


def _entry(
    provider: str,
    label: str,
    country: str,
    language: str,
    source_kind: str,
    interaction_mode: str,
    description: str,
    usage_guide: str,
    search_url: str,
    profile_url: str,
    recommended_for: str,
    notes: str,
) -> ExternalSourceCatalogEntry:
    return ExternalSourceCatalogEntry(
        provider=provider,
        label=label,
        country=country,
        language=language,
        source_kind=source_kind,
        interaction_mode=interaction_mode,
        description=description,
        usage_guide=usage_guide,
        search_url=search_url,
        profile_url=profile_url,
        recommended_for=recommended_for,
        notes=notes,
        **_SAFE,
    )


SOURCE_CATALOG["free_work"] = _entry(
    provider="free_work",
    label="Free-Work",
    country="FR",
    language="fr",
    source_kind="freelance_mission_board",
    interaction_mode="searchable_job_board",
    description=(
        "French job board spécialisé dans les missions en freelance "
        "et CDI pour les professionnels de la tech et de l'IT."
    ),
    usage_guide=(
        "Utiliser le site Free-Work pour rechercher manuellement des missions "
        "freelance IT. Filtrer par contrat 'freelance/contractor'. "
        "Copier les offres pertinentes dans SORIA manuellement."
    ),
    search_url="https://www.free-work.com/fr/tech-it/jobs?contracts=contractor",
    profile_url="https://www.free-work.com/fr/tech-it",
    recommended_for="Missions freelance IT en France, support technique",
    notes="Free-Work est un job board passif. Aucune API publique.",
)

SOURCE_CATALOG["codeur"] = _entry(
    provider="codeur",
    label="Codeur.com",
    country="FR",
    language="fr",
    source_kind="freelance_project_marketplace",
    interaction_mode="project_marketplace",
    description=(
        "Marketplace de projets freelance pour développeurs, "
        "avec mise en relation entre clients et freelances."
    ),
    usage_guide=(
        "Naviguer sur Codeur.com pour identifier des projets freelance. "
        "Noter les missions pertinentes et les référencer dans SORIA "
        "à titre d'information. Ne pas automatiser les réponses."
    ),
    search_url="https://www.codeur.com/mission-freelance",
    profile_url="https://www.codeur.com/",
    recommended_for="Projets de développement web et mobile, missions courtes",
    notes="Plateforme de mise en relation. Pas d'API publique documentée.",
)

SOURCE_CATALOG["lehibou"] = _entry(
    provider="lehibou",
    label="LeHibou",
    country="FR",
    language="fr",
    source_kind="freelance_it_matching_platform",
    interaction_mode="searchable_or_account_based_matching",
    description=(
        "Plateforme de mise en relation entre freelances IT "
        "et entreprises pour des missions de conseil et d'expertise."
    ),
    usage_guide=(
        "Créer un compte freelance sur LeHibou pour accéder aux missions. "
        "Utiliser la recherche d'annonces pour identifier les opportunités. "
        "Référencer manuellement dans SORIA les missions pertinentes."
    ),
    search_url="https://www.lehibou.com/en/recherche/annonces",
    profile_url="https://www.lehibou.com/en/freelance",
    recommended_for="Missions IT et conseil en France, freelances expérimentés",
    notes="Nécessite un compte freelance pour postuler. Pas d'API publique.",
)

SOURCE_CATALOG["malt"] = _entry(
    provider="malt",
    label="Malt",
    country="FR",
    language="fr",
    source_kind="freelance_profile_marketplace",
    interaction_mode="profile_marketplace",
    description=(
        "Plateforme leader en Europe pour la mise en relation entre "
        "freelances et clients, avec gestion des paiements intégrée."
    ),
    usage_guide=(
        "Créer et maintenir un profil Malt à jour. "
        "Explorer les missions disponibles via le tableau de bord Malt. "
        "Référencer les missions pertinentes dans SORIA manuellement."
    ),
    search_url="https://www.malt.fr/",
    profile_url="https://www.malt.fr/c/freelancers",
    recommended_for="Missions freelance tous domaines, networking, récurrence",
    notes="API GraphQL non documentée publiquement. Utilisation manuelle recommandée.",
)

SOURCE_CATALOG["comet"] = _entry(
    provider="comet",
    label="Comet",
    country="FR",
    language="fr",
    source_kind="freelance_it_matching_platform",
    interaction_mode="curated_profile_matching",
    description=(
        "Plateforme de mise en relation curatorée pour freelances IT, "
        "avec approche personnalisée et accompagnement."
    ),
    usage_guide=(
        "S'inscrire sur Comet en tant que freelance. "
        "Les missions sont proposées par les account managers Comet. "
        "Référencer manuellement les opportunités dans SORIA."
    ),
    search_url="https://www.comet.co/fr/freelances/trouver-une-mission",
    profile_url="https://www.comet.co/fr/freelances/trouver-une-mission",
    recommended_for="Missions IT sélectionnées, freelances avec expertise pointue",
    notes="Approche curatorée — les missions sont proposées, pas librement consultables.",
)


def get_source_catalog() -> list[ExternalSourceCatalogEntry]:
    """Return the full source catalog as a list."""
    return list(SOURCE_CATALOG.values())
