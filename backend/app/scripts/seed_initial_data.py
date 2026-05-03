"""Initial seed data for SORIA AI Prospecting Platform.

Run with: python -m app.scripts.seed_initial_data
Idempotent: safe to run multiple times.
"""

import sys
from pathlib import Path

# Ensure backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session, select

from app.core.database import engine
from app.core.enums import ServiceCategoryStatus
from app.models.academy_category import AcademyCategory
from app.models.offer import Offer
from app.models.service_category import ServiceCategory

SEED_SERVICE_CATEGORIES = [
    {
        "name": "Formation IT & DevOps",
        "slug": "formation-it-devops",
        "description": "Formations en informatique, réseaux et DevOps",
        "position": 1,
    },
    {
        "name": "Cloud & Infrastructure",
        "slug": "cloud-infrastructure",
        "description": "Solutions Cloud et infrastructure IT",
        "position": 2,
    },
    {
        "name": "DevOps & Automation",
        "slug": "devops-automation",
        "description": "Automatisation, CI/CD et pipelines DevOps",
        "position": 3,
    },
    {
        "name": "Cybersecurity, Monitoring & SOC-ready",
        "slug": "cybersecurity-monitoring-soc",
        "description": "Cybersécurité, SOC et monitoring",
        "position": 4,
    },
    {
        "name": "IAM, SSO & Access Security",
        "slug": "iam-sso-access-security",
        "description": "Gestion des identités et sécurité des accès",
        "position": 5,
    },
]

SEED_ACADEMY_CATEGORIES = [
    {"name": "Réseaux & Services d'infrastructure", "slug": "reseaux-services-infrastructure"},
    {"name": "Linux & Administration système", "slug": "linux-administration-systeme"},
    {"name": "Docker & Conteneurisation", "slug": "docker-conteneurisation"},
    {"name": "Kubernetes & Déploiement applicatif", "slug": "kubernetes-deploiement-applicatif"},
    {"name": "DevOps, CI/CD & Automatisation", "slug": "devops-cicd-automatisation"},
    {"name": "SOC, SIEM & Threat Intelligence", "slug": "soc-siem-threat-intelligence"},
    {"name": "Monitoring & Observabilité", "slug": "monitoring-observabilite"},
    {"name": "IAM, SSO & Sécurisation des accès", "slug": "iam-sso-securisation-acces"},
    {
        "name": "Infrastructure as Code & Configuration Management",
        "slug": "infrastructure-as-code-configuration-management",
    },
]

SEED_OFFERS = [
    {
        "name": "Formation BTS SIO / SISR",
        "slug": "formation-bts-sio-sisr",
        "short_description": "Formation complète BTS SIO option SISR",
        "priority": 10,
        "category_slug": "formation-it-devops",
    },
    {
        "name": "Atelier Linux Administration",
        "slug": "atelier-linux-administration",
        "short_description": "Atelier pratique d'administration Linux",
        "priority": 9,
        "category_slug": "formation-it-devops",
    },
    {
        "name": "Atelier Réseaux & Services d'infrastructure",
        "slug": "atelier-reseaux-services-infrastructure",
        "short_description": "Atelier sur les réseaux et services",
        "priority": 8,
        "category_slug": "formation-it-devops",
    },
    {
        "name": "Formation Docker pratique",
        "slug": "formation-docker-pratique",
        "short_description": "Formation pratique à Docker et la conteneurisation",
        "priority": 7,
        "category_slug": "formation-it-devops",
    },
    {
        "name": "Formation Kubernetes / K3s",
        "slug": "formation-kubernetes-k3s",
        "short_description": "Formation à Kubernetes et K3s",
        "priority": 6,
        "category_slug": "formation-it-devops",
    },
    {
        "name": "Audit CI/CD",
        "slug": "audit-cicd",
        "short_description": "Audit de pipeline CI/CD existant",
        "priority": 5,
        "category_slug": "devops-automation",
    },
    {
        "name": "Déploiement Kubernetes K3s",
        "slug": "deploiement-kubernetes-k3s",
        "short_description": "Mise en place et déploiement Kubernetes K3s",
        "priority": 4,
        "category_slug": "devops-automation",
    },
    {
        "name": "Monitoring infrastructure",
        "slug": "monitoring-infrastructure",
        "short_description": "Mise en place de monitoring d'infrastructure",
        "priority": 3,
        "category_slug": "cybersecurity-monitoring-soc",
    },
    {
        "name": "SOC-ready Wazuh Lab",
        "slug": "soc-ready-wazuh-lab",
        "short_description": "Laboratoire Wazuh pour SOC",
        "priority": 2,
        "category_slug": "cybersecurity-monitoring-soc",
    },
    {
        "name": "Keycloak SSO setup",
        "slug": "keycloak-sso-setup",
        "short_description": "Installation et configuration Keycloak SSO",
        "priority": 1,
        "category_slug": "iam-sso-access-security",
    },
    {
        "name": "Infrastructure as Code with Ansible & Terraform",
        "slug": "iac-ansible-terraform",
        "short_description": "Automatisation d'infrastructure avec Ansible et Terraform",
        "priority": 0,
        "category_slug": "devops-automation",
    },
]


def _upsert_service_categories(session: Session) -> dict[str, ServiceCategory]:
    """Insert or skip ServiceCategory rows by slug. Returns slug->obj map."""
    cat_map = {}
    for data in SEED_SERVICE_CATEGORIES:
        existing = session.exec(select(ServiceCategory).where(ServiceCategory.slug == data["slug"])).first()
        if existing:
            print(f"  ServiceCategory '{data['name']}' already exists, skipping.")
            cat_map[existing.slug] = existing
        else:
            cat = ServiceCategory(
                name=data["name"],
                slug=data["slug"],
                description=data.get("description"),
                position=data.get("position", 0),
                status=ServiceCategoryStatus.active,
            )
            session.add(cat)
            session.flush()
            cat_map[cat.slug] = cat
            print(f"  Created ServiceCategory '{data['name']}'.")
    return cat_map


def _upsert_academy_categories(session: Session) -> None:
    """Insert or skip AcademyCategory rows by slug."""
    for data in SEED_ACADEMY_CATEGORIES:
        existing = session.exec(select(AcademyCategory).where(AcademyCategory.slug == data["slug"])).first()
        if existing:
            print(f"  AcademyCategory '{data['name']}' already exists, skipping.")
        else:
            ac = AcademyCategory(
                name=data["name"],
                slug=data["slug"],
                is_active=True,
            )
            session.add(ac)
            print(f"  Created AcademyCategory '{data['name']}'.")


def _upsert_offers(session: Session, cat_map: dict[str, ServiceCategory]) -> None:
    """Insert or skip Offer rows by slug, linked to the correct ServiceCategory."""
    for data in SEED_OFFERS:
        existing = session.exec(select(Offer).where(Offer.slug == data["slug"])).first()
        if existing:
            print(f"  Offer '{data['name']}' already exists, skipping.")
        else:
            cat_slug = data["category_slug"]
            category = cat_map[cat_slug]
            offer = Offer(
                category_id=category.id,
                name=data["name"],
                slug=data["slug"],
                short_description=data.get("short_description"),
                priority=data.get("priority", 0),
                is_active=True,
            )
            session.add(offer)
            print(f"  Created Offer '{data['name']}' (→ {cat_slug}).")


def seed():
    with Session(engine) as session:
        print("Seeding service categories...")
        cat_map = _upsert_service_categories(session)

        print("Seeding academy categories...")
        _upsert_academy_categories(session)

        print("Seeding offers...")
        _upsert_offers(session, cat_map)

        session.commit()
        print("Seed completed.")


if __name__ == "__main__":
    seed()
