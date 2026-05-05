"""CRUD API tests for companies, contacts, and opportunities."""

from uuid import uuid4


def _create_company(client, **overrides):
    """Helper to create a company via API."""
    payload = {
        "name": "Test Company",
        "domain": "testcompany.fr",
        "city": "Paris",
        "source": "manual",
        "status": "new",
        "company_type": "unknown",
        "country": "France",
    }
    payload.update(overrides)
    return client.post("/api/v1/companies", json=payload)


def test_create_company(client):
    resp = _create_company(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Company"
    assert data["domain"] == "testcompany.fr"
    assert data["city"] == "Paris"
    assert data["country"] == "France"
    assert data["status"] == "new"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_list_companies(client):
    _create_company(client, name="Company A")
    _create_company(client, name="Company B")

    resp = client.get("/api/v1/companies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_companies_filters_by_search(client):
    _create_company(client, name="Alpha Corp", domain="alpha.fr", city="Lyon")
    _create_company(client, name="Beta Inc", domain="beta.fr", city="Marseille")

    # Search by name
    resp = client.get("/api/v1/companies?search=Alpha")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # Search by domain
    resp = client.get("/api/v1/companies?search=beta.fr")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # Search by city
    resp = client.get("/api/v1/companies?search=Lyon")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_companies_filters_by_status_and_type(client):
    _create_company(client, name="Qualified Co", status="qualified")
    _create_company(client, name="New Co", status="new")

    resp = client.get("/api/v1/companies?status=qualified")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_company_by_id(client):
    create_resp = _create_company(client)
    company_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/companies/{company_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Company"


def test_get_company_not_found(client):
    resp = client.get(f"/api/v1/companies/{uuid4()}")
    assert resp.status_code == 404


def test_get_company_invalid_id(client):
    resp = client.get("/api/v1/companies/not-a-uuid")
    assert resp.status_code == 400


def test_patch_company(client):
    create_resp = _create_company(client)
    company_id = create_resp.json()["id"]

    resp = client.patch(f"/api/v1/companies/{company_id}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    # Other fields unchanged
    assert resp.json()["domain"] == "testcompany.fr"


def test_patch_company_not_found(client):
    resp = client.patch(f"/api/v1/companies/{uuid4()}", json={"name": "Nope"})
    assert resp.status_code == 404


# --- Contact tests ---


def _create_contact(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean.dupont@example.com",
        "contact_type": "director",
        "source": "manual",
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


def test_create_contact(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = _create_contact(client, company_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Jean Dupont"
    assert data["email"] == "jean.dupont@example.com"
    assert data["company_id"] == str(company_id)
    assert data["contact_type"] == "director"


def test_create_contact_full_name_auto_generated(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    # Only first_name and last_name, no full_name
    resp = client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(company_id),
            "first_name": "Marie",
            "last_name": "Curie",
            "contact_type": "unknown",
            "source": "manual",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["full_name"] == "Marie Curie"


def test_create_contact_custom_full_name(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(company_id),
            "first_name": "Marie",
            "last_name": "Curie",
            "full_name": "Dr. Marie Curie",
            "contact_type": "unknown",
            "source": "manual",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["full_name"] == "Dr. Marie Curie"


def test_create_contact_no_company(client):
    resp = client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(uuid4()),
            "first_name": "Ghost",
            "contact_type": "unknown",
            "source": "manual",
        },
    )
    assert resp.status_code == 400
    assert "company" in resp.json()["detail"].lower()


def test_list_contacts(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    _create_contact(client, company_id, first_name="Alice")
    _create_contact(client, company_id, first_name="Bob")

    resp = client.get("/api/v1/contacts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_list_contacts_filter_by_company(client):
    c1 = _create_company(client, name="Company A").json()
    c2 = _create_company(client, name="Company B").json()

    _create_contact(client, c1["id"])
    _create_contact(client, c2["id"])

    resp = client.get(f"/api/v1/contacts?company_id={c1['id']}")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_contact_by_id(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    create_resp = _create_contact(client, company_id)
    contact_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/contacts/{contact_id}")
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Jean"


def test_patch_contact(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    create_resp = _create_contact(client, company_id)
    contact_id = create_resp.json()["id"]

    resp = client.patch(f"/api/v1/contacts/{contact_id}", json={"role_title": "CEO"})
    assert resp.status_code == 200
    assert resp.json()["role_title"] == "CEO"


# --- Opportunity tests ---


def test_create_opportunity(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "Formation DevOps",
            "opportunity_type": "devops_cloud",
            "source": "manual",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Formation DevOps"
    assert data["company_id"] == str(company_id)
    assert data["status"] == "new"
    assert data["priority"] == "medium"


def test_create_opportunity_with_score(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "Scored Opportunity",
            "score": 75,
            "source": "manual",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["score"] == 75


def test_create_opportunity_no_company(client):
    resp = client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(uuid4()),
            "title": "Orphan",
            "source": "manual",
        },
    )
    assert resp.status_code == 400
    assert "company" in resp.json()["detail"].lower()


def test_create_opportunity_with_nonexistent_contact(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "Bad Contact",
            "contact_id": str(uuid4()),
            "source": "manual",
        },
    )
    assert resp.status_code == 400
    assert "contact" in resp.json()["detail"].lower()


def test_create_opportunity_score_gt_100(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "Invalid Score",
            "score": 150,
            "source": "manual",
        },
    )
    assert resp.status_code == 422


def test_create_opportunity_score_lt_0(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    resp = client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "Negative Score",
            "score": -5,
            "source": "manual",
        },
    )
    assert resp.status_code == 422


def test_list_opportunities(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    client.post(
        "/api/v1/opportunities",
        json={"company_id": str(company_id), "title": "Opp A", "source": "manual"},
    )
    client.post(
        "/api/v1/opportunities",
        json={"company_id": str(company_id), "title": "Opp B", "source": "manual"},
    )

    resp = client.get("/api/v1/opportunities")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_get_opportunity_by_id(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/opportunities",
        json={"company_id": str(company_id), "title": "Find Me", "source": "manual"},
    )
    opp_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/opportunities/{opp_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Find Me"


def test_patch_opportunity(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/opportunities",
        json={"company_id": str(company_id), "title": "Original Title", "source": "manual"},
    )
    opp_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/opportunities/{opp_id}",
        json={"title": "Updated Title", "priority": "high"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["priority"] == "high"


def test_opportunity_filters(client):
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "DevOps Training",
            "opportunity_type": "devops_cloud",
            "status": "new",
            "priority": "high",
            "score": 80,
            "source": "manual",
        },
    )
    client.post(
        "/api/v1/opportunities",
        json={
            "company_id": str(company_id),
            "title": "Security Audit",
            "opportunity_type": "cybersecurity_soc",
            "status": "scored",
            "priority": "medium",
            "score": 40,
            "source": "manual",
        },
    )

    # Filter by type
    resp = client.get("/api/v1/opportunities?opportunity_type=devops_cloud")
    assert resp.json()["total"] == 1

    # Filter by min_score
    resp = client.get("/api/v1/opportunities?min_score=50")
    assert resp.json()["total"] == 1

    # Filter by search
    resp = client.get("/api/v1/opportunities?search=Security")
    assert resp.json()["total"] == 1


def test_health_endpoint_still_works(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "SORIA AI Prospecting Platform"


# --- Scoring & Draft generation tests (Phase 5a) ---


def _setup_company_contact_opportunity(client):
    """Create a company, contact, and opportunity linked together."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    contact_resp = _create_contact(client, company_id)
    assert contact_resp.status_code == 201
    contact_id = contact_resp.json()["id"]

    opp_resp = _create_opportunity(client, company_id, contact_id=contact_id)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    return company_id, contact_id, opp_id


def test_score_opportunity(client):
    """Score an existing opportunity and verify the response."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(f"/api/v1/opportunities/{opp_id}/score")
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert isinstance(data["score"], int)
    assert 0 <= data["score"] <= 100
    assert "explanation" in data
    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 0
    assert "breakdown" in data
    assert isinstance(data["breakdown"], dict)
    assert "opportunity" in data
    assert data["opportunity"]["id"] == opp_id
    # Opportunity should have score set now
    assert data["opportunity"]["score"] == data["score"]


def test_score_opportunity_not_found(client):
    """Scoring a non-existent opportunity returns 404."""
    resp = client.post(f"/api/v1/opportunities/{uuid4()}/score")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_generate_draft_creates_message_draft(client):
    """Generate a draft for an opportunity and verify it creates a MessageDraft."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunity_id"] == opp_id
    assert data["status"] == "draft"
    assert data["generated_by"] == "rule_based"
    assert data["message_type"] == "prospecting_email"
    assert data["body"] is not None
    assert len(data["body"]) > 0
    assert "id" in data
    assert "created_at" in data


def test_generate_draft_remains_draft(client):
    """Generated draft must stay in draft status (not auto-submitted)."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_generate_draft_does_not_create_duplicate(client):
    """Second generate-draft call returns the existing active rule_based draft."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp1.status_code == 200
    first_id = resp1.json()["id"]

    resp2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == first_id
    assert resp2.json()["status"] == "draft"

    # Verify only one draft exists for this opportunity
    drafts_resp = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
    assert drafts_resp.json()["total"] == 1


def test_generate_draft_allow_new_after_archive(client):
    """After archiving a rule_based draft, generate-draft creates a new one."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create first draft
    resp1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    first_id = resp1.json()["id"]

    # Archive it
    client.post(f"/api/v1/message-drafts/{first_id}/archive")

    # Generate again — should create a new draft
    resp2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp2.status_code == 200
    assert resp2.json()["id"] != first_id


def test_generate_draft_not_found(client):
    """Draft generation for a non-existent opportunity returns 404."""
    resp = client.post(f"/api/v1/opportunities/{uuid4()}/generate-draft")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# --- Enrichment tests (Phase 5c) ---


def _create_devops_opportunity(client, company_id, **overrides):
    """Create a DevOps-type opportunity with minimal data."""
    payload = {
        "company_id": str(company_id),
        "title": "Formation Kubernetes et CI/CD",
        "opportunity_type": "devops_cloud",
        "description": "Migration infrastructure Cloud avec Docker et Kubernetes",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


def _create_formation_opportunity(client, company_id, **overrides):
    """Create a formation-type opportunity."""
    payload = {
        "company_id": str(company_id),
        "title": "BTS SIO — Formation Informatique",
        "opportunity_type": "formation",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


def _create_training_center_company(client, **overrides):
    payload = {
        "name": "CFA des Métiers",
        "company_type": "cfa",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/companies", json=payload)


def test_enrich_updates_detected_need_and_next_action(client):
    """Enriching an opportunity sets detected_need and next_action."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    opp_resp = _create_devops_opportunity(client, company_id)
    opp_id = opp_resp.json()["id"]
    assert opp_resp.json()["detected_need"] is None

    resp = client.post(f"/api/v1/opportunities/{opp_id}/enrich")
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] is True
    assert len(data["detected_need"]) > 0
    assert "DevOps" in data["detected_need"] or "automatisation" in data["detected_need"]
    assert len(data["recommended_landing_page"]) > 0
    assert data["recommended_landing_page"].startswith("/")
    assert len(data["next_action"]) > 0
    assert len(data["explanation"]) > 0
    assert "opportunity" in data
    # Verify the opportunity was updated in the DB
    get_resp = client.get(f"/api/v1/opportunities/{opp_id}")
    assert get_resp.json()["detected_need"] == data["detected_need"]
    assert get_resp.json()["recommended_landing_page"] == data["recommended_landing_page"]
    assert get_resp.json()["next_action"] == data["next_action"]


def test_enrich_formation_with_training_center(client):
    """Enriching a formation opportunity for a CFA detects training need."""
    company_resp = _create_training_center_company(client)
    company_id = company_resp.json()["id"]

    opp_resp = _create_formation_opportunity(client, company_id)
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/enrich")
    assert resp.status_code == 200
    data = resp.json()
    assert "formation" in data["detected_need"].lower() or "pédagogique" in data["detected_need"].lower()
    assert "formation" in data["recommended_landing_page"]


def test_enrich_not_found(client):
    """Enriching a non-existent opportunity returns 404."""
    resp = client.post(f"/api/v1/opportunities/{uuid4()}/enrich")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_enrich_does_not_overwrite_existing_detected_need(client):
    """Enrichment does not overwrite a non-empty detected_need."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    opp_resp = _create_devops_opportunity(client, company_id)
    opp_id = opp_resp.json()["id"]

    # Manually set a detected_need first
    client.patch(
        f"/api/v1/opportunities/{opp_id}",
        json={"detected_need": "Besoin spécifique déjà identifié par l'utilisateur"},
    )

    resp = client.post(f"/api/v1/opportunities/{opp_id}/enrich")
    assert resp.status_code == 200
    data = resp.json()
    # The existing value must be preserved
    assert "déjà identifié" in data["detected_need"]
    assert data["detected_need_overwritten"] is False


def test_generate_draft_uses_enriched_detected_need(client):
    """Generated draft body should reference the enriched detected_need."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    opp_resp = _create_devops_opportunity(client, company_id)
    opp_id = opp_resp.json()["id"]

    # Enrich first
    client.post(f"/api/v1/opportunities/{opp_id}/enrich")

    # Then generate draft
    draft_resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert draft_resp.status_code == 200
    body = draft_resp.json()["body"]
    # Body should reference the enriched need or the title
    assert "Kubernetes" in body or "formation" in body.lower() or "accompagnons" in body.lower()


# --- Regenerate draft tests (Phase 5c) ---


def test_regenerate_draft_archives_old_and_creates_new(client):
    """Regenerate archives the existing active rule_based draft and creates a new one."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create first draft
    resp1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    first_id = resp1.json()["id"]

    # Regenerate
    resp2 = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert resp2.status_code == 200
    new_id = resp2.json()["id"]
    assert new_id != first_id
    assert resp2.json()["status"] == "draft"

    # Verify old draft is archived
    get_old = client.get(f"/api/v1/message-drafts/{first_id}")
    assert get_old.json()["status"] == "archived"

    # Verify new draft is active
    assert resp2.json()["status"] == "draft"


def test_regenerate_draft_does_not_archive_sent_manually(client):
    """Regenerate must NOT archive sent_manually drafts (even if rule_based)."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create a rule_based draft via generate-draft (status = draft)
    resp1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    first_id = resp1.json()["id"]

    # Promote it through the workflow to sent_manually
    client.post(f"/api/v1/message-drafts/{first_id}/submit-review", json={})
    client.post(f"/api/v1/message-drafts/{first_id}/approve", json={})
    client.post(f"/api/v1/message-drafts/{first_id}/mark-sent-manually")
    get_sent = client.get(f"/api/v1/message-drafts/{first_id}")
    assert get_sent.json()["status"] == "sent_manually"

    # Create a second active rule_based draft
    # First archive the sent one so we can create a new one
    # (actually generate-draft checks for active drafts, and sent is not active)
    resp2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    second_id = resp2.json()["id"]
    assert second_id != first_id

    # Regenerate — should archive second_id but NOT first_id (sent_manually)
    resp3 = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert resp3.status_code == 200

    # Check sent_manually draft is untouched
    get_first = client.get(f"/api/v1/message-drafts/{first_id}")
    assert get_first.json()["status"] == "sent_manually"

    # Check old active draft is archived
    get_second = client.get(f"/api/v1/message-drafts/{second_id}")
    assert get_second.json()["status"] == "archived"


def test_regenerate_draft_not_found(client):
    """Regenerate on a non-existent opportunity returns 404."""
    resp = client.post(f"/api/v1/opportunities/{uuid4()}/regenerate-draft")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_generate_draft_still_prevents_duplicate_after_enrich(client):
    """Generate-draft duplicate prevention still works after enrichment."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    opp_resp = _create_devops_opportunity(client, company_id)
    opp_id = opp_resp.json()["id"]

    # Enrich
    client.post(f"/api/v1/opportunities/{opp_id}/enrich")

    # Generate first draft
    resp1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    first_id = resp1.json()["id"]

    # Generate again — should return same draft
    resp2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp2.json()["id"] == first_id


def test_regenerated_draft_status_is_draft(client):
    """The newly created draft after regenerate must have status draft."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")

    resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"
