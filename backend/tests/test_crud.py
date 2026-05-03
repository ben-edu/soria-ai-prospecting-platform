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
