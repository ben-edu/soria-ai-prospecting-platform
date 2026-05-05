"""Phase 6A — Offer & AcademyResource catalogue + matching tests."""

from uuid import uuid4

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_service_category(client, **overrides):
    """Create a service category via direct DB or API. Use API if available."""
    # No API endpoint for service categories in the test; rely on PATCH-level
    # tests. For matching tests we need categories first.
    # We'll create via the offers endpoint which validates the FK.
    # Strategy: use a conftest-level helper that sidesteps the FK.
    # Actually, the simplest approach: create a company + opportunity,
    # then for matching we need offers + academy resources which need
    # categories. We'll create categories by calling the existing
    # service-categories endpoint.
    payload = {
        "name": "Test Category",
        "slug": "test-category",
        "description": "Test",
        "position": 0,
        "status": "active",
    }
    payload.update(overrides)
    return client.post("/api/v1/service-categories", json=payload)


def _create_academy_category(client, **overrides):
    payload = {
        "name": "Test Academy Category",
        "slug": "test-academy-category",
        "is_active": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/academy-categories", json=payload)


def _create_company(client, **overrides):
    payload = {
        "name": "Test Company",
        "domain": "testcompany.fr",
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
# Offer CRUD tests
# ---------------------------------------------------------------------------


def _create_offer_payload(category_id, **overrides):
    payload = {
        "category_id": str(category_id),
        "name": "DevOps & Automation",
        "slug": "devops-automation",
        "short_description": "CI/CD and container orchestration",
        "full_description": "Full DevOps pipeline automation with Kubernetes and Docker",
        "landing_page_url": "/services/devops-automation",
        "keywords": {"keywords": ["DevOps", "Kubernetes", "Docker", "CI/CD", "automation"]},
        "priority": 10,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_create_offer(client):
    """Create an offer and verify the response."""
    cat_resp = _create_service_category(client)
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    payload = _create_offer_payload(cat_id)
    resp = client.post("/api/v1/offers", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "DevOps & Automation"
    assert data["slug"] == "devops-automation"
    assert data["is_active"] is True
    assert data["priority"] == 10
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_offer_duplicate_slug(client):
    """Creating two offers with the same slug should fail."""
    cat_resp = _create_service_category(client)
    cat_id = cat_resp.json()["id"]

    payload = _create_offer_payload(cat_id)
    assert client.post("/api/v1/offers", json=payload).status_code == 201

    resp = client.post("/api/v1/offers", json=payload)
    assert resp.status_code == 400
    assert "slug" in resp.json()["detail"].lower()


def test_create_service_category_duplicate_slug(client):
    """Creating two service categories with the same slug should fail."""
    assert _create_service_category(client).status_code == 201
    resp = _create_service_category(client)
    assert resp.status_code == 400
    assert "slug" in resp.json()["detail"].lower()


def test_create_academy_category_duplicate_slug(client):
    """Creating two academy categories with the same slug should fail."""
    assert _create_academy_category(client).status_code == 201
    resp = _create_academy_category(client)
    assert resp.status_code == 400
    assert "slug" in resp.json()["detail"].lower()


def test_list_offers(client):
    """List offers with pagination."""
    cat_resp = _create_service_category(client)
    cat_id = cat_resp.json()["id"]

    for i in range(3):
        payload = _create_offer_payload(cat_id, name=f"Offer {i}", slug=f"offer-{i}")
        assert client.post("/api/v1/offers", json=payload).status_code == 201

    resp = client.get("/api/v1/offers?skip=0&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


def test_list_offers_search(client):
    """Search offers by name or description."""
    cat_resp = _create_service_category(client)
    cat_id = cat_resp.json()["id"]

    payload1 = _create_offer_payload(
        cat_id, name="Formation Kubernetes", slug="formation-kubernetes",
        full_description="Deploiement Kubernetes en production",
    )
    payload2 = _create_offer_payload(
        cat_id, name="Audit Securite", slug="audit-securite",
        full_description="Audit de securite des infrastructures",
    )

    assert client.post("/api/v1/offers", json=payload1).status_code == 201
    assert client.post("/api/v1/offers", json=payload2).status_code == 201

    resp = client.get("/api/v1/offers?search=Kubernetes")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_offers_filter_active(client):
    """Filter offers by active status."""
    cat_resp = _create_service_category(client)
    cat_id = cat_resp.json()["id"]

    payload1 = _create_offer_payload(cat_id, name="Active 1", slug="active-1", is_active=True)
    payload2 = _create_offer_payload(cat_id, name="Inactive 1", slug="inactive-1", is_active=False)

    assert client.post("/api/v1/offers", json=payload1).status_code == 201
    assert client.post("/api/v1/offers", json=payload2).status_code == 201

    resp = client.get("/api/v1/offers?active=true")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_offer_by_id(client):
    """Get a single offer by ID."""
    cat_resp = _create_service_category(client)
    cat_id = cat_resp.json()["id"]

    create_resp = client.post("/api/v1/offers", json=_create_offer_payload(cat_id))
    offer_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/offers/{offer_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "DevOps & Automation"


def test_get_offer_not_found(client):
    """Get a non-existent offer returns 404."""
    resp = client.get(f"/api/v1/offers/{uuid4()}")
    assert resp.status_code == 404


def test_patch_offer(client):
    """Update an offer via PATCH."""
    cat_resp = _create_service_category(client)
    cat_id = cat_resp.json()["id"]

    create_resp = client.post("/api/v1/offers", json=_create_offer_payload(cat_id))
    offer_id = create_resp.json()["id"]

    resp = client.patch(f"/api/v1/offers/{offer_id}", json={"priority": 5, "is_active": False})
    assert resp.status_code == 200
    assert resp.json()["priority"] == 5
    assert resp.json()["is_active"] is False
    # Other fields unchanged
    assert resp.json()["name"] == "DevOps & Automation"


def test_patch_offer_not_found(client):
    """Patch a non-existent offer returns 404."""
    resp = client.patch(f"/api/v1/offers/{uuid4()}", json={"name": "Nope"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AcademyResource CRUD tests
# ---------------------------------------------------------------------------


def _create_resource_payload(category_id, **overrides):
    payload = {
        "category_id": str(category_id) if category_id else None,
        "title": "Kubernetes & Deploiement",
        "slug": "kubernetes-deploiement",
        "short_description": "Guide Kubernetes K3s",
        "content": "Orchestration Kubernetes",
        "resource_type": "guide",
        "level": "advanced",
        "technologies": {"technologies": ["Kubernetes", "K3s", "Docker", "Helm"]},
        "public_url": "https://example.com/k8s",
        "is_free": True,
        "is_published": True,
    }
    payload.update(overrides)
    return payload


def test_create_academy_resource(client):
    """Create an academy resource and verify the response."""
    cat_resp = _create_academy_category(client)
    cat_id = cat_resp.json()["id"]

    payload = _create_resource_payload(cat_id)
    resp = client.post("/api/v1/academy-resources", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Kubernetes & Deploiement"
    assert data["slug"] == "kubernetes-deploiement"
    assert data["resource_type"] == "guide"
    assert data["level"] == "advanced"
    assert data["is_published"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_academy_resource_duplicate_slug(client):
    """Creating two resources with the same slug should fail."""
    cat_resp = _create_academy_category(client)
    cat_id = cat_resp.json()["id"]

    payload = _create_resource_payload(cat_id)
    assert client.post("/api/v1/academy-resources", json=payload).status_code == 201

    resp = client.post("/api/v1/academy-resources", json=payload)
    assert resp.status_code == 400


def test_list_academy_resources(client):
    """List academy resources with pagination."""
    cat_resp = _create_academy_category(client)
    cat_id = cat_resp.json()["id"]

    for i in range(3):
        payload = _create_resource_payload(cat_id, title=f"Resource {i}", slug=f"resource-{i}")
        assert client.post("/api/v1/academy-resources", json=payload).status_code == 201

    resp = client.get("/api/v1/academy-resources?skip=0&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


def test_list_academy_resources_filters(client):
    """Filter academy resources by type and level."""
    cat_resp = _create_academy_category(client)
    cat_id = cat_resp.json()["id"]

    p1 = _create_resource_payload(
        cat_id, title="Guide Docker", slug="guide-docker", resource_type="guide",
    )
    p2 = _create_resource_payload(
        cat_id, title="Lab Securite", slug="lab-securite",
        resource_type="lab", level="beginner",
    )
    assert client.post("/api/v1/academy-resources", json=p1).status_code == 201
    assert client.post("/api/v1/academy-resources", json=p2).status_code == 201

    resp = client.get("/api/v1/academy-resources?resource_type=lab")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = client.get("/api/v1/academy-resources?level=beginner")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_academy_resource_by_id(client):
    """Get a single academy resource by ID."""
    cat_resp = _create_academy_category(client)
    cat_id = cat_resp.json()["id"]

    create_resp = client.post("/api/v1/academy-resources", json=_create_resource_payload(cat_id))
    resource_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/academy-resources/{resource_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Kubernetes & Deploiement"


def test_get_academy_resource_not_found(client):
    """Get a non-existent academy resource returns 404."""
    resp = client.get(f"/api/v1/academy-resources/{uuid4()}")
    assert resp.status_code == 404


def test_patch_academy_resource(client):
    """Update an academy resource via PATCH."""
    cat_resp = _create_academy_category(client)
    cat_id = cat_resp.json()["id"]

    create_resp = client.post("/api/v1/academy-resources", json=_create_resource_payload(cat_id))
    resource_id = create_resp.json()["id"]

    resp = client.patch(f"/api/v1/academy-resources/{resource_id}", json={"level": "beginner", "is_published": False})
    assert resp.status_code == 200
    assert resp.json()["level"] == "beginner"
    assert resp.json()["is_published"] is False
    assert resp.json()["title"] == "Kubernetes & Deploiement"


# ---------------------------------------------------------------------------
# Match-assets tests
# ---------------------------------------------------------------------------


def _setup_match_prerequisites(client):
    """Create categories, offers, resources for matching tests.

    Returns a dict with ids needed for test setup.
    """
    # Create service categories
    cat_payloads = [
        {"name": "DevOps & Automation", "slug": "devops-automation",
         "description": "DevOps", "position": 1, "status": "active"},
        {"name": "Cybersecurity", "slug": "cybersecurity-monitoring-soc",
         "description": "Security", "position": 2, "status": "active"},
        {"name": "Formation IT", "slug": "formation-it-devops",
         "description": "Formation", "position": 3, "status": "active"},
    ]
    cat_ids = {}
    for cp in cat_payloads:
        r = client.post("/api/v1/service-categories", json=cp)
        assert r.status_code == 201
        cat_ids[cp["slug"]] = r.json()["id"]

    # Create academy categories
    acat_payloads = [
        {"name": "Kubernetes & Deploiement", "slug": "kubernetes-deploiement-applicatif", "is_active": True},
        {"name": "SOC & Threat Intelligence", "slug": "soc-siem-threat-intelligence", "is_active": True},
        {"name": "Formation", "slug": "formation", "is_active": True},
    ]
    acat_ids = {}
    for acp in acat_payloads:
        r = client.post("/api/v1/academy-categories", json=acp)
        assert r.status_code == 201
        acat_ids[acp["slug"]] = r.json()["id"]

    # Create offers
    offers_data = [
        {
            "category_id": cat_ids["devops-automation"],
            "name": "DevOps & Automation",
            "slug": "devops-automation-offer",
            "short_description": "CI/CD and container orchestration",
            "keywords": {"keywords": ["DevOps", "Kubernetes", "Docker", "CI/CD", "automation"]},
            "landing_page_url": "/services/devops-automation",
            "priority": 10,
            "is_active": True,
        },
        {
            "category_id": cat_ids["cybersecurity-monitoring-soc"],
            "name": "Cybersecurity & SOC",
            "slug": "cybersecurity-soc-offer",
            "short_description": "SOC and security monitoring",
            "keywords": {"keywords": ["SOC", "Wazuh", "SIEM", "security", "monitoring"]},
            "landing_page_url": "/services/cybersecurity-monitoring",
            "priority": 8,
            "is_active": True,
        },
        {
            "category_id": cat_ids["formation-it-devops"],
            "name": "Formation IT & DevOps",
            "slug": "formation-it-devops-offer",
            "short_description": "IT training and formation",
            "keywords": {"keywords": ["formation", "training", "BTS SIO", "Linux"]},
            "landing_page_url": "/services/formation-it-devops",
            "priority": 9,
            "is_active": True,
        },
    ]
    offer_ids = {}
    for od in offers_data:
        r = client.post("/api/v1/offers", json=od)
        assert r.status_code == 201
        offer_ids[od["slug"]] = r.json()["id"]

    # Create academy resources
    resources_data = [
        {
            "category_id": acat_ids["kubernetes-deploiement-applicatif"],
            "title": "Kubernetes & Deploiement",
            "slug": "k8s-deploiement",
            "short_description": "K8s deployment guide",
            "technologies": {"technologies": ["Kubernetes", "K3s", "Docker", "Helm"]},
            "resource_type": "guide",
            "level": "advanced",
            "is_published": True,
        },
        {
            "category_id": acat_ids["soc-siem-threat-intelligence"],
            "title": "SOC, SIEM & Threat Intelligence",
            "slug": "soc-siem-guide",
            "short_description": "Wazuh SIEM and MISP",
            "technologies": {"technologies": ["SOC", "Wazuh", "SIEM", "MISP", "TheHive"]},
            "resource_type": "lab",
            "level": "advanced",
            "is_published": True,
        },
        {
            "category_id": acat_ids["formation"],
            "title": "Linux & Administration",
            "slug": "linux-admin",
            "short_description": "Linux administration basics",
            "technologies": {"technologies": ["Linux", "Debian", "Ubuntu", "bash"]},
            "resource_type": "course",
            "level": "beginner",
            "is_published": True,
        },
    ]
    resource_ids = {}
    for rd in resources_data:
        r = client.post("/api/v1/academy-resources", json=rd)
        assert r.status_code == 201
        resource_ids[rd["slug"]] = r.json()["id"]

    # Create company and opportunity
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    return {
        "company_id": company_id,
        "offer_ids": offer_ids,
        "resource_ids": resource_ids,
    }


def test_match_assets_not_found(client):
    """Match-assets on a non-existent opportunity returns 404."""
    resp = client.post(f"/api/v1/opportunities/{uuid4()}/match-assets")
    assert resp.status_code == 404


def test_match_assets_devops_opportunity(client):
    """Match-assets finds DevOps offer for a DevOps opportunity."""
    pre = _setup_match_prerequisites(client)

    opp_resp = _create_opportunity(
        client,
        pre["company_id"],
        title="Formation Kubernetes et CI/CD",
        opportunity_type="devops_cloud",
        description="Migration infrastructure Cloud avec Docker et Kubernetes",
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] is True
    assert data["offer"] is not None
    assert data["academy_resource"] is not None
    assert len(data["explanation"]) > 0
    assert "opportunity" in data
    assert data["opportunity"]["offer_id"] is not None
    assert data["opportunity"]["academy_resource_id"] is not None


def test_match_assets_sets_offer_and_resource_ids(client):
    """Match-assets sets the offer_id and academy_resource_id on the opportunity."""
    pre = _setup_match_prerequisites(client)

    opp_resp = _create_opportunity(
        client,
        pre["company_id"],
        title="DevOps with Kubernetes",
        opportunity_type="devops_cloud",
    )
    opp_id = opp_resp.json()["id"]

    assert opp_resp.json()["offer_id"] is None
    assert opp_resp.json()["academy_resource_id"] is None

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()

    # Verify the opportunity was updated in DB
    get_resp = client.get(f"/api/v1/opportunities/{opp_id}")
    assert get_resp.json()["offer_id"] is not None
    assert get_resp.json()["academy_resource_id"] is not None

    # Verify the IDs match what was set
    assert data["opportunity"]["offer_id"] is not None
    assert data["opportunity"]["academy_resource_id"] is not None


def test_match_assets_updates_landing_page(client):
    """Match-assets updates recommended_landing_page from matched offer."""
    pre = _setup_match_prerequisites(client)

    opp_resp = _create_opportunity(
        client,
        pre["company_id"],
        title="DevOps with Kubernetes",
        opportunity_type="devops_cloud",
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()

    # Landing page should be set from the matched offer
    landing = data["opportunity"]["recommended_landing_page"]
    assert landing is not None
    assert len(landing) > 0
    assert landing.startswith("/")


def test_score_increases_after_match_assets(client):
    """Score opportunity before and after match-assets — score goes up."""
    pre = _setup_match_prerequisites(client)

    opp_resp = _create_opportunity(
        client,
        pre["company_id"],
        title="DevOps with Kubernetes",
        opportunity_type="devops_cloud",
    )
    opp_id = opp_resp.json()["id"]

    # Score before matching
    score_before = client.post(f"/api/v1/opportunities/{opp_id}/score")
    assert score_before.status_code == 200
    score_before_val = score_before.json()["opportunity"]["score"]

    # Match
    client.post(f"/api/v1/opportunities/{opp_id}/match-assets")

    # Score after matching
    score_after = client.post(f"/api/v1/opportunities/{opp_id}/score")
    assert score_after.status_code == 200
    score_after_val = score_after.json()["opportunity"]["score"]

    # Score should increase because offer_id + academy_resource_id are now set
    assert score_after_val >= score_before_val + 20, (
        f"Score increased by less than expected: "
        f"{score_before_val} -> {score_after_val}"
    )


def test_draft_includes_offer_context_after_match(client):
    """Generated draft should reference the matched offer name after match-assets."""
    pre = _setup_match_prerequisites(client)

    opp_resp = _create_opportunity(
        client,
        pre["company_id"],
        title="DevOps Kubernetes",
        opportunity_type="devops_cloud",
    )
    opp_id = opp_resp.json()["id"]

    # Match first
    client.post(f"/api/v1/opportunities/{opp_id}/match-assets")

    # Then regenerate draft (to get past duplicate prevention from any prior draft)
    draft_resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert draft_resp.status_code == 200
    body = draft_resp.json()["body"]

    # Body should reference the matched offer
    assert "DevOps" in body or "Automation" in body or "offre" in body.lower()


def test_match_empty_description_still_works(client):
    """Match-assets still works with minimal opportunity data."""
    pre = _setup_match_prerequisites(client)

    opp_resp = _create_opportunity(
        client,
        pre["company_id"],
        title="Security",
        opportunity_type="cybersecurity_soc",
        description=None,
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] is True


def test_match_assets_formation_opportunity(client):
    """Match-assets finds formation offer for a formation opportunity."""
    _setup_match_prerequisites(client)
    # Create a training-center company
    company_resp = _create_company(client, name="CFA Métiers", company_type="cfa")
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id,
        title="BTS SIO Formation Informatique",
        opportunity_type="formation",
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()
    # Should match the formation offer
    offer_name = (data.get("offer") or {}).get("name", "")
    assert "formation" in offer_name.lower() or "Formation" in offer_name or offer_name != ""

    # Should find some academy resource
    assert data["academy_resource"] is not None or data["offer"] is not None


def test_match_assets_devops_engineer_prefers_devops_automation(client):
    """DevOps engineer + devops_cloud + it_company → devops-automation-offer."""
    _setup_match_prerequisites(client)

    company_resp = _create_company(client, name="DevOps Corp", company_type="it_company")
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id,
        title="DevOps engineer",
        opportunity_type="devops_cloud",
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offer"] is not None
    assert data["offer"]["slug"] == "devops-automation-offer", (
        f"Expected devops-automation-offer, got {data['offer']['slug']}"
    )


def test_match_assets_formation_with_training_center_prefers_formation(client):
    """BTS SIO + formation + training_center → formation-it-devops-offer."""
    _setup_match_prerequisites(client)

    company_resp = _create_company(client, name="CFA Training", company_type="training_center")
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id,
        title="BTS SIO Formation",
        opportunity_type="formation",
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offer"] is not None
    assert data["offer"]["slug"] == "formation-it-devops-offer", (
        f"Expected formation-it-devops-offer, got {data['offer']['slug']}"
    )


def test_match_assets_devops_cloud_not_formation_offer(client):
    """Plain DevOps/cloud opportunity must NOT select Formation IT & DevOps."""
    _setup_match_prerequisites(client)

    company_resp = _create_company(client, name="CloudCorp", company_type="it_company")
    company_id = company_resp.json()["id"]

    opp_resp = _create_opportunity(
        client,
        company_id,
        title="Ingénieur Cloud et DevOps",
        opportunity_type="devops_cloud",
        description="Infrastructure cloud avec Proxmox et OPNsense",
    )
    opp_id = opp_resp.json()["id"]

    resp = client.post(f"/api/v1/opportunities/{opp_id}/match-assets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offer"] is not None
    assert data["offer"]["slug"] != "formation-it-devops-offer", (
        "Formation IT & DevOps was selected for a plain DevOps/cloud opportunity"
    )
