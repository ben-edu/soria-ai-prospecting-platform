"""Phase 7A — Opportunity OpenProject manual link field."""


def _create_company(client, **overrides):
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


def _create_opportunity(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "title": "Formation DevOps",
        "opportunity_type": "devops_cloud",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


# ---------------------------------------------------------------------------
# 1) Create opportunity with openproject_work_package_id
# ---------------------------------------------------------------------------


def test_create_opportunity_with_openproject_work_package_id(client):
    """Opportunity can be created with openproject_work_package_id set."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    resp = _create_opportunity(
        client,
        company_id,
        openproject_work_package_id="42",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["openproject_work_package_id"] == "42"


# ---------------------------------------------------------------------------
# 2) Patch opportunity with openproject_work_package_id
# ---------------------------------------------------------------------------


def test_patch_opportunity_with_openproject_work_package_id(client):
    """Opportunity can be patched with openproject_work_package_id."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    resp = _create_opportunity(client, company_id)
    assert resp.status_code == 201
    opp_id = resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/opportunities/{opp_id}",
        json={"openproject_work_package_id": "99"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["openproject_work_package_id"] == "99"


# ---------------------------------------------------------------------------
# 3) GET single opportunity includes the field
# ---------------------------------------------------------------------------


def test_get_opportunity_includes_openproject_work_package_id(client):
    """GET /api/v1/opportunities/{id} includes openproject_work_package_id."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    resp = _create_opportunity(
        client,
        company_id,
        openproject_work_package_id="7",
    )
    assert resp.status_code == 201
    opp_id = resp.json()["id"]

    get_resp = client.get(f"/api/v1/opportunities/{opp_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["openproject_work_package_id"] == "7"


# ---------------------------------------------------------------------------
# 4) List opportunities includes the field
# ---------------------------------------------------------------------------


def test_list_opportunities_includes_openproject_work_package_id(client):
    """GET /api/v1/opportunities includes openproject_work_package_id."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    create_resp = _create_opportunity(
        client,
        company_id,
        openproject_work_package_id="123",
    )
    assert create_resp.status_code == 201
    opp_id = create_resp.json()["id"]

    list_resp = client.get("/api/v1/opportunities")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]

    matched = next((item for item in items if item["id"] == opp_id), None)
    assert matched is not None
    assert matched["openproject_work_package_id"] == "123"


# ---------------------------------------------------------------------------
# 5) Create opportunity without the field still works
# ---------------------------------------------------------------------------


def test_create_opportunity_without_openproject_work_package_id(client):
    """Opportunity created without openproject_work_package_id defaults to null."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    resp = _create_opportunity(client, company_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["openproject_work_package_id"] is None
    assert "title" in data
    assert data["company_id"] == str(company_id)
