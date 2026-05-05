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
from app.core.enums import AcademyLevel, AcademyResourceType, ServiceCategoryStatus
from app.models.academy_category import AcademyCategory
from app.models.academy_resource import AcademyResource
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
        "name": "Formation IT & DevOps",
        "slug": "formation-it-devops",
        "short_description": (
            "Formation complète en informatique, réseaux et DevOps — "
            "BTS SIO, SISR, Linux, Docker, Kubernetes"
        ),
        "full_description": (
            "Catalogue de formations couvrant l'ensemble du spectre IT : "
            "administration Linux, réseaux, conteneurisation Docker, orchestration Kubernetes, "
            "et fondamentaux DevOps. Adapté aux centres de formation, CFA et établissements scolaires."
        ),
        "target_audience": {"list": ["centres de formation", "CFA", "écoles", "étudiants BTS SIO", "apprentis"]},
        "keywords": {
            "keywords": [
                "formation", "BTS SIO", "SISR", "Linux",
                "réseaux", "Docker", "Kubernetes", "DevOps",
            ]
        },
        "landing_page_url": "/services/formation-it-devops",
        "priority": 10,
        "category_slug": "formation-it-devops",
    },
    {
        "name": "Cloud & Infrastructure",
        "slug": "cloud-infrastructure",
        "short_description": "Solutions Cloud et infrastructure IT — Linux, Proxmox, OPNsense, VPN, hébergement",
        "full_description": (
            "Accompagnement à la mise en place et à l'administration d'infrastructures Cloud : "
            "virtualisation Proxmox, firewall OPNsense, VPN site-to-site, reverse proxy HAProxy, "
            "TLS et gestion de certificats."
        ),
        "target_audience": {"list": ["PME", "startups", "entreprises", "hébergeurs", "DSI"]},
        "keywords": {
            "keywords": [
                "Linux", "Proxmox", "OPNsense", "HAProxy",
                "Traefik", "TLS", "VPN", "infrastructure",
            ]
        },
        "landing_page_url": "/services/cloud-infrastructure",
        "priority": 9,
        "category_slug": "cloud-infrastructure",
    },
    {
        "name": "DevOps & Automation",
        "slug": "devops-automation",
        "short_description": "Automatisation, CI/CD, conteneurisation et pipelines DevOps",
        "full_description": (
            "Mise en place de pipelines CI/CD complets : Jenkins, GitLab CI, Harbor, "
            "déploiement Kubernetes (K3s), Infrastructure as Code avec Ansible et Terraform, "
            "et automatisation des processus de release."
        ),
        "target_audience": {"list": ["équipes DevOps", "développeurs", "administrateurs système", "DSI"]},
        "keywords": {
            "keywords": [
                "DevOps", "CI/CD", "Jenkins", "Docker", "Kubernetes", "K3s", "Harbor", "automation",
                "Ansible", "Terraform",
            ]
        },
        "landing_page_url": "/services/devops-automation",
        "priority": 8,
        "category_slug": "devops-automation",
    },
    {
        "name": "Cybersecurity, Monitoring & SOC-ready",
        "slug": "cybersecurity-monitoring-soc",
        "short_description": "Cybersécurité, SOC, SIEM et monitoring d'infrastructure",
        "full_description": (
            "Mise en place d'une stack SOC complète : Wazuh SIEM, MISP Threat Intelligence, "
            "TheHive pour la gestion d'incidents, dashboards de monitoring, "
            "durcissement des infrastructures et audit de conformité."
        ),
        "target_audience": {"list": ["DSI", "RSSI", "équipes sécurité", "PME", "collectivités"]},
        "keywords": {
            "keywords": [
                "SOC", "Wazuh", "SIEM", "monitoring", "logs", "MISP", "TheHive",
                "hardening", "cybersécurité", "sécurité",
            ]
        },
        "landing_page_url": "/services/cybersecurity-monitoring",
        "priority": 7,
        "category_slug": "cybersecurity-monitoring-soc",
    },
    {
        "name": "IAM, SSO & Access Security",
        "slug": "iam-sso-access-security",
        "short_description": "Gestion des identités, SSO et sécurité des accès",
        "full_description": (
            "Déploiement de solutions IAM/SSO : Keycloak, authentification multifacteur (MFA), "
            "fédération OAuth2 / OpenID Connect, RBAC, gestion des annuaires LDAP/AD, "
            "et sécurisation des accès VPN et applications."
        ),
        "target_audience": {"list": ["DSI", "RSSI", "PME", "startups", "collectivités"]},
        "keywords": {
            "keywords": [
                "IAM", "SSO", "Keycloak", "MFA", "OAuth2", "OpenID Connect",
                "RBAC", "VPN", "annuaire", "LDAP",
            ]
        },
        "landing_page_url": "/services/iam-sso-access-security",
        "priority": 6,
        "category_slug": "iam-sso-access-security",
    },
]

SEED_ACADEMY_RESOURCES = [
    {
        "title": "Réseaux & Services d'infrastructure",
        "slug": "reseaux-services-infrastructure",
        "short_description": "Guide complet sur les réseaux et services d'infrastructure",
        "content": "Réseaux TCP/IP, VLAN, routage, services DNS/DHCP, firewall, OPNsense.",
        "resource_type": AcademyResourceType.guide,
        "level": AcademyLevel.intermediate,
        "technologies": {
            "technologies": ["TCP/IP", "VLAN", "DNS", "DHCP", "OPNsense", "HAProxy", "firewall"],
        },
        "category_slug": "reseaux-services-infrastructure",
    },
    {
        "title": "Linux & Administration système",
        "slug": "linux-administration-systeme",
        "short_description": "Formation à l'administration de systèmes Linux",
        "content": "Administration Debian/Ubuntu, gestion des utilisateurs, services systemd, sécurisation.",
        "resource_type": AcademyResourceType.course,
        "level": AcademyLevel.beginner,
        "technologies": {
            "technologies": ["Linux", "Debian", "Ubuntu", "systemd", "bash", "administration"],
        },
        "category_slug": "linux-administration-systeme",
    },
    {
        "title": "Docker & Conteneurisation",
        "slug": "docker-conteneurisation",
        "short_description": "Atelier pratique Docker et conteneurisation",
        "content": "Docker, Docker Compose, images, registres, networking, volumes, bonnes pratiques.",
        "resource_type": AcademyResourceType.workshop,
        "level": AcademyLevel.intermediate,
        "technologies": {
            "technologies": ["Docker", "Docker Compose", "conteneurisation", "registry", "Harbor"],
        },
        "category_slug": "docker-conteneurisation",
    },
    {
        "title": "Kubernetes & Déploiement applicatif",
        "slug": "kubernetes-deploiement-applicatif",
        "short_description": "Guide Kubernetes K3s pour le déploiement applicatif",
        "content": "Orchestration Kubernetes, K3s, déploiement, services, ingress, stockage, Helm.",
        "resource_type": AcademyResourceType.guide,
        "level": AcademyLevel.advanced,
        "technologies": {
            "technologies": ["Kubernetes", "K3s", "Helm", "ingress", "déploiement", "orchestration"],
        },
        "category_slug": "kubernetes-deploiement-applicatif",
    },
    {
        "title": "DevOps, CI/CD & Automatisation",
        "slug": "devops-cicd-automatisation",
        "short_description": "Pratiques DevOps et pipelines CI/CD",
        "content": "CI/CD Jenkins, GitLab CI, GitHub Actions, automatisation Ansible, Terraform.",
        "resource_type": AcademyResourceType.course,
        "level": AcademyLevel.intermediate,
        "technologies": {
            "technologies": [
                "DevOps", "CI/CD", "Jenkins", "GitLab CI", "GitHub Actions",
                "Ansible", "Terraform", "automatisation",
            ]
        },
        "category_slug": "devops-cicd-automatisation",
    },
    {
        "title": "SOC, SIEM & Threat Intelligence",
        "slug": "soc-siem-threat-intelligence",
        "short_description": "Mise en place d'un SOC avec Wazuh et MISP",
        "content": "Architecture SOC, SIEM Wazuh, MISP Threat Intelligence, TheHive, détection d'incidents.",
        "resource_type": AcademyResourceType.lab,
        "level": AcademyLevel.advanced,
        "technologies": {
            "technologies": ["SOC", "Wazuh", "SIEM", "MISP", "TheHive", "Threat Intelligence", "détection"],
        },
        "category_slug": "soc-siem-threat-intelligence",
    },
    {
        "title": "Monitoring & Observabilité",
        "slug": "monitoring-observabilite",
        "short_description": "Stack de monitoring et observabilité",
        "content": "Prometheus, Grafana, Loki, alerting, dashboards, métriques applicatives et infrastructure.",
        "resource_type": AcademyResourceType.guide,
        "level": AcademyLevel.intermediate,
        "technologies": {
            "technologies": ["Prometheus", "Grafana", "Loki", "monitoring", "observabilité", "alerting"],
        },
        "category_slug": "monitoring-observabilite",
    },
    {
        "title": "IAM, SSO & Sécurisation des accès",
        "slug": "iam-sso-securisation-acces",
        "short_description": "Guide IAM et SSO avec Keycloak",
        "content": "Keycloak, OAuth2, OpenID Connect, MFA, RBAC, fédération d'identités, annuaire LDAP.",
        "resource_type": AcademyResourceType.guide,
        "level": AcademyLevel.intermediate,
        "technologies": {
            "technologies": ["Keycloak", "OAuth2", "OpenID Connect", "MFA", "IAM", "SSO", "RBAC", "LDAP"],
        },
        "category_slug": "iam-sso-securisation-acces",
    },
    {
        "title": "Infrastructure as Code & Configuration Management",
        "slug": "infrastructure-as-code-configuration-management",
        "short_description": "Automatisation d'infrastructure avec Ansible et Terraform",
        "content": "Ansible, Terraform, gestion de configuration, provisioning Cloud, GitOps.",
        "resource_type": AcademyResourceType.course,
        "level": AcademyLevel.advanced,
        "technologies": {
            "technologies": ["Ansible", "Terraform", "IaC", "GitOps", "provisioning", "configuration"],
        },
        "category_slug": "infrastructure-as-code-configuration-management",
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


def _upsert_academy_categories(session: Session) -> dict[str, AcademyCategory]:
    """Insert or skip AcademyCategory rows by slug. Returns slug->obj map."""
    cat_map = {}
    for data in SEED_ACADEMY_CATEGORIES:
        existing = session.exec(select(AcademyCategory).where(AcademyCategory.slug == data["slug"])).first()
        if existing:
            print(f"  AcademyCategory '{data['name']}' already exists, skipping.")
            cat_map[existing.slug] = existing
        else:
            ac = AcademyCategory(
                name=data["name"],
                slug=data["slug"],
                is_active=True,
            )
            session.add(ac)
            session.flush()
            cat_map[ac.slug] = ac
            print(f"  Created AcademyCategory '{data['name']}'.")
    return cat_map


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
                full_description=data.get("full_description"),
                target_audience=data.get("target_audience"),
                keywords=data.get("keywords"),
                landing_page_url=data.get("landing_page_url"),
                priority=data.get("priority", 0),
                is_active=True,
            )
            session.add(offer)
            print(f"  Created Offer '{data['name']}' (→ {cat_slug}).")


def _upsert_academy_resources(session: Session, cat_map: dict[str, AcademyCategory]) -> None:
    """Insert or skip AcademyResource rows by slug, linked to the correct AcademyCategory."""
    for data in SEED_ACADEMY_RESOURCES:
        existing = session.exec(select(AcademyResource).where(AcademyResource.slug == data["slug"])).first()
        if existing:
            print(f"  AcademyResource '{data['title']}' already exists, skipping.")
        else:
            cat_slug = data["category_slug"]
            category = cat_map.get(cat_slug)
            resource = AcademyResource(
                category_id=category.id if category else None,
                title=data["title"],
                slug=data["slug"],
                short_description=data.get("short_description"),
                content=data.get("content"),
                resource_type=data.get("resource_type", AcademyResourceType.guide),
                level=data.get("level", AcademyLevel.beginner),
                technologies=data.get("technologies"),
                is_published=True,
                is_free=True,
            )
            session.add(resource)
            print(f"  Created AcademyResource '{data['title']}' (→ {cat_slug}).")


def seed():
    with Session(engine) as session:
        print("Seeding service categories...")
        cat_map = _upsert_service_categories(session)

        print("Seeding academy categories...")
        acat_map = _upsert_academy_categories(session)

        print("Seeding offers...")
        _upsert_offers(session, cat_map)

        print("Seeding academy resources...")
        _upsert_academy_resources(session, acat_map)

        session.commit()
        print("Seed completed.")


if __name__ == "__main__":
    seed()
