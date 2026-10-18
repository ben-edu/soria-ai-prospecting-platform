"""Idempotently synchronize the frozen MVCS B2B commercial offer catalog."""

from sqlmodel import Session, select

from app.core.database import engine
from app.core.enums import ServiceCategoryStatus
from app.models.offer import Offer
from app.models.service_category import ServiceCategory

CATEGORY = {
    "name": "Solutions B2B déploiement & fiabilité",
    "slug": "solutions-b2b-deploiement-fiabilite",
    "description": "Offres SORIA orientées problèmes, déploiement et fiabilité de production",
    "position": 0,
}

OFFERS = [
    {
        "name": "Diagnostic déploiement & infrastructure",
        "slug": "diagnostic-deploiement-infrastructure",
        "short_description": (
            "Diagnostic borné pour clarifier les risques de déploiement, "
            "d'infrastructure et les prochaines actions prioritaires."
        ),
        "full_description": (
            "Analyse ciblée de la chaîne de déploiement et de l'infrastructure "
            "avec constats, risques, priorités et recommandations actionnables."
        ),
        "target_audience": {
            "primary": "software / SaaS / online-product teams with a live product"
        },
        "keywords": {
            "keywords": [
                "diagnostic",
                "déploiement",
                "infrastructure",
                "devops",
                "cloud",
                "kubernetes",
                "plateforme",
            ]
        },
        "landing_page_url": (
            "https://soria-ai.fr/solutions/diagnostic-deploiement-infrastructure/"
        ),
        "priority": 100,
    },
    {
        "name": "Industrialisation des déploiements",
        "slug": "industrialisation-deploiements",
        "short_description": (
            "Rendre les déploiements reproductibles, contrôlés et moins dépendants "
            "d'opérations manuelles."
        ),
        "full_description": (
            "Industrialisation CI/CD, automatisation et contrôle du chemin de release "
            "à partir de l'existant, avec documentation et vérification."
        ),
        "target_audience": {
            "primary": "software / SaaS / online-product teams with a live product"
        },
        "keywords": {
            "keywords": [
                "ci/cd",
                "pipeline",
                "déploiement",
                "release",
                "gitops",
                "automation",
                "reproductible",
            ]
        },
        "landing_page_url": (
            "https://soria-ai.fr/solutions/industrialisation-deploiements/"
        ),
        "priority": 90,
    },
    {
        "name": "Fiabilité de production & exploitation",
        "slug": "fiabilite-production-exploitation",
        "short_description": (
            "Réduire les fragilités d'exploitation et mieux maîtriser la production, "
            "la reprise et les changements."
        ),
        "full_description": (
            "Travail ciblé sur la fiabilité de production, l'observabilité, les procédures "
            "d'exploitation, la reprise et la vérification des changements."
        ),
        "target_audience": {
            "primary": "software / SaaS / online-product teams with a live product"
        },
        "keywords": {
            "keywords": [
                "production",
                "reliability",
                "fiabilité",
                "sre",
                "observabilité",
                "monitoring",
                "recovery",
                "exploitation",
            ]
        },
        "landing_page_url": (
            "https://soria-ai.fr/solutions/fiabilite-production-exploitation/"
        ),
        "priority": 80,
    },
]


def sync_mvcs_b2b_catalog(session: Session) -> None:
    category = session.exec(
        select(ServiceCategory).where(ServiceCategory.slug == CATEGORY["slug"])
    ).first()
    if category is None:
        category = ServiceCategory(
            name=CATEGORY["name"],
            slug=CATEGORY["slug"],
            description=CATEGORY["description"],
            position=CATEGORY["position"],
            status=ServiceCategoryStatus.active,
            is_active=True,
        )
    else:
        category.name = CATEGORY["name"]
        category.description = CATEGORY["description"]
        category.position = CATEGORY["position"]
        category.status = ServiceCategoryStatus.active
        category.is_active = True

    session.add(category)
    session.flush()

    for data in OFFERS:
        offer = session.exec(select(Offer).where(Offer.slug == data["slug"])).first()
        if offer is None:
            offer = Offer(category_id=category.id, name=data["name"], slug=data["slug"])

        offer.category_id = category.id
        offer.name = data["name"]
        offer.short_description = data["short_description"]
        offer.full_description = data["full_description"]
        offer.target_audience = data["target_audience"]
        offer.keywords = data["keywords"]
        offer.landing_page_url = data["landing_page_url"]
        offer.priority = data["priority"]
        offer.is_active = True
        session.add(offer)


def seed() -> None:
    with Session(engine) as session:
        sync_mvcs_b2b_catalog(session)
        session.commit()
        print("MVCS B2B offer catalog synchronized.")


if __name__ == "__main__":
    seed()
