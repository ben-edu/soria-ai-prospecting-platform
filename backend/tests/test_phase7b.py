"""Phase 7B — OpenProject Work Package Preview for an Opportunity."""

import uuid

import pytest


def _create_company(client, **overrides):
    payload = {
        "name": "Test Company",
        "domain": "testcompany.fr",
        "city": "Paris",
        "country": "France",
        "source": "manual",
        "status": "new",
        "company_type": "unknown",
    }
    payload.update(overrides)
    return client.post("/api/v1/companies", json=payload)


def _create_contact(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "first_name": "Jean",
        "last_name": "Dupont",
        "full_name": "Jean Dupont",
        "role_title": "CTO",
        "email": "jean@testcompany.fr",
        "source": "manual",
        "contact_type": "director",
    }
    payload.update(overrides)
    return client.post("/api/v1/contacts", json=payload)


def _create_opportunity(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "title": "Formation DevOps",
        "opportunity_type": "devops_cloud",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


def _create_offer(client, **overrides):
    payload = {
        "name": "Accompagnement DevOps",
        "slug": "accompagnement-devops",
        "short_description": "Formation DevOps complète",
        "landing_page_url": "https://soria.academy/devops",
        "is_active": True,
    }
    payload.update(overrides)
    from app.core.enums import ServiceCategoryStatus

    cat_resp = client.post(
        "/api/v1/service-categories",
        json={"name": "DevOps", "slug": "devops", "status": ServiceCategoryStatus.active.value},
    )
    cat_id = cat_resp.json()["id"]
    payload["category_id"] = str(cat_id)
    return client.post("/api/v1/offers", json=payload)


def _create_academy_resource(client, **overrides):
    payload = {
        "title": "Guide DevOps",
        "slug": "guide-devops",
        "short_description": "Un guide complet",
        "resource_type": "guide",
        "level": "beginner",
        "public_url": "https://soria.academy/guide-devops",
        "is_published": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/academy-resources", json=payload)


# ---------------------------------------------------------------------------
# 1) Missing opportunity returns 404
# ---------------------------------------------------------------------------


def test_preview_missing_opportunity_returns_404(client):
    """GET /api/v1/opportunities/{uuid}/openproject-preview with
    non-existent UUID returns 404."""
    missing_id = uuid.uuid4()
    resp = client.get(f"/api/v1/opportunities/{missing_id}/openproject-preview")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2) Invalid UUID returns 400
# ---------------------------------------------------------------------------


def test_preview_invalid_uuid_returns_400(client):
    """GET with an invalid UUID returns 400."""
    resp = client.get("/api/v1/opportunities/not-a-uuid/openproject-preview")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3) Basic preview returns subject + description
# ---------------------------------------------------------------------------


def test_preview_returns_subject_and_description(client):
    """Preview endpoint returns subject and description for a basic
    opportunity."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(client, company_id)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    preview_resp = client.get(
        f"/api/v1/opportunities/{opp_id}/openproject-preview"
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()

    assert data["suggested_type"] == "Opportunity"
    assert data["suggested_status"] == "To analyse"
    assert data["suggested_priority"] == "Normal"
    assert "[SORIA]" in data["subject"]
    assert "Formation DevOps" in data["subject"]
    assert "Test Company" in data["subject"]
    assert "# Opportunité SORIA" in data["description"]
    assert "## Résumé" in data["description"]
    assert "## Entreprise" in data["description"]
    assert "## Contact" in data["description"]
    assert "## Qualification" in data["description"]
    assert "## Offre / Ressource associée" in data["description"]
    assert "## Suivi recommandé" in data["description"]
    assert "## Conformité" in data["description"]
    assert "## Liens / références" in data["description"]
    assert "Aucun message externe ne doit être envoyé sans validation humaine." in data["description"]
    assert data["copy_hint"] == (
        "Copy the subject and description above into a new OpenProject work package."
    )
    assert "opportunity" in data
    assert data["opportunity"]["id"] == str(opp_id)


# ---------------------------------------------------------------------------
# 4) Preview includes company and contact info when linked
# ---------------------------------------------------------------------------


def test_preview_includes_company_and_contact(client):
    """Preview includes company name/type/location and contact details when
    linked."""
    company_resp = _create_company(
        client,
        name="ACME Corp",
        company_type="enterprise",
        website_url="https://acme.fr",
        city="Lyon",
        country="France",
    )
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    contact_resp = _create_contact(
        client,
        company_id=company_id,
        full_name="Marie Curie",
        role_title="CEO",
        email="marie@acme.fr",
    )
    assert contact_resp.status_code == 201
    contact_id = contact_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id=company_id,
        contact_id=contact_id,
    )
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    preview_resp = client.get(
        f"/api/v1/opportunities/{opp_id}/openproject-preview"
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()

    # Subject includes company
    assert "ACME Corp" in data["subject"]
    assert "[SORIA]" in data["subject"]

    # Description includes company info
    desc = data["description"]
    assert "ACME Corp" in desc
    assert "enterprise" in desc
    assert "https://acme.fr" in desc
    assert "Lyon" in desc
    assert "France" in desc

    # Description includes contact info
    assert "Marie Curie" in desc
    assert "CEO" in desc
    assert "marie@acme.fr" in desc


# ---------------------------------------------------------------------------
# 5) Preview includes offer and academy resource when linked
# ---------------------------------------------------------------------------


def test_preview_includes_offer_and_academy_resource(client):
    """Preview includes offer name/url and academy resource title/urls when
    linked."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    offer_resp = _create_offer(client)
    assert offer_resp.status_code == 201
    offer_id = offer_resp.json()["id"]

    resource_resp = _create_academy_resource(client)
    assert resource_resp.status_code == 201
    resource_id = resource_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id=company_id,
        offer_id=offer_id,
        academy_resource_id=resource_id,
    )
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    preview_resp = client.get(
        f"/api/v1/opportunities/{opp_id}/openproject-preview"
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()

    desc = data["description"]
    assert "Accompagnement DevOps" in desc
    assert "https://soria.academy/devops" in desc
    assert "Guide DevOps" in desc
    assert "https://soria.academy/guide-devops" in desc


# ---------------------------------------------------------------------------
# 6) Preview maps priority/status correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soria_status,expected_op_status",
    [
        ("new", "To analyse"),
        ("to_analyze", "To analyse"),
        ("scored", "To analyse"),
        ("interesting", "To analyse"),
        ("draft_needed", "To analyse"),
        ("draft_ready", "To analyse"),
        ("waiting_validation", "Draft prepared"),
        ("approved", "Draft prepared"),
        ("sent", "Contacted"),
        ("follow_up_needed", "Contacted"),
        ("response_received", "Follow-up"),
        ("meeting_scheduled", "Meeting"),
        ("converted", "Won"),
        ("lost", "Lost"),
        ("closed", "Lost"),
        ("not_relevant", "Lost"),
    ],
)
def test_preview_status_mapping(client, soria_status, expected_op_status):
    """Preview maps each SORIA status to the correct OpenProject-style
    status."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(client, company_id, status=soria_status)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    preview_resp = client.get(
        f"/api/v1/opportunities/{opp_id}/openproject-preview"
    )
    assert preview_resp.status_code == 200
    assert preview_resp.json()["suggested_status"] == expected_op_status


@pytest.mark.parametrize(
    "soria_priority,expected_op_priority",
    [
        ("urgent", "High"),
        ("high", "High"),
        ("medium", "Normal"),
        ("low", "Low"),
    ],
)
def test_preview_priority_mapping(client, soria_priority, expected_op_priority):
    """Preview maps each SORIA priority to the correct OpenProject-style
    priority."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(client, company_id, priority=soria_priority)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    preview_resp = client.get(
        f"/api/v1/opportunities/{opp_id}/openproject-preview"
    )
    assert preview_resp.status_code == 200
    assert preview_resp.json()["suggested_priority"] == expected_op_priority


# ---------------------------------------------------------------------------
# 7) Preview does not mutate the opportunity
# ---------------------------------------------------------------------------


def test_preview_does_not_modify_opportunity(client):
    """Preview endpoint does not change openproject_work_package_id, status,
    or any other field on the opportunity."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id,
        status="new",
        priority="low",
        score=None,
    )
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    # Read original state
    original = client.get(f"/api/v1/opportunities/{opp_id}").json()

    # Call preview
    preview_resp = client.get(
        f"/api/v1/opportunities/{opp_id}/openproject-preview"
    )
    assert preview_resp.status_code == 200

    # Read state after preview
    after = client.get(f"/api/v1/opportunities/{opp_id}").json()

    assert after["openproject_work_package_id"] == original["openproject_work_package_id"]
    assert after["status"] == original["status"]
    assert after["priority"] == original["priority"]
    assert after["score"] == original["score"]
    assert after == original
