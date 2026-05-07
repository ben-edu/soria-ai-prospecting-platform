"""Phase 9B — Import External Candidate into SourceRecord + Company + Opportunity.

Covers:
- Import france_travail candidate creates SourceRecord + Company + Opportunity
- Import adzuna_uk candidate creates SourceRecord + Company + Opportunity with source=other and language=en
- Import freelancer candidate creates Opportunity with source_kind/freelance budget details in notes
- Duplicate import of same provider + external_id does not create duplicate SourceRecord
- Duplicate import returns same or existing Opportunity where possible
- Unknown provider returns 400
- Import does NOT create MessageDraft
- Import does NOT create FollowUp
- Import does NOT create ComplianceEvent
- SourceRecord.raw_payload contains provider/external_id/title
- Opportunity notes contain provider and external_id
- Existing company with same name/country is reused
"""

from sqlmodel import Session

from app.core.enums import OpportunityType, SourceType
from app.models.company import Company
from app.models.compliance_event import ComplianceEvent
from app.models.follow_up import FollowUp
from app.models.message_draft import MessageDraft
from app.models.opportunity import Opportunity
from app.models.source_record import SourceRecord

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_FT_CANDIDATE = {
    "provider": "france_travail",
    "external_id": "fr-001",
    "source_kind": "job",
    "title": "Ingénieur DevOps",
    "company_name": "TechCorp France",
    "description": "Recherche ingénieur DevOps expérimenté.",
    "location": "Paris",
    "country": "FR",
    "language": "fr",
    "source_url": "https://example.com/fr-001",
    "source_published_at": "2025-06-01T00:00:00+00:00",
    "contract_type": "CDI",
    "remote_type": "hybrid",
    "budget_min": None,
    "budget_max": None,
    "budget_currency": None,
    "tags": ["devops", "cloud", "ci/cd", "kubernetes"],
    "raw_payload": {
        "provider": "france_travail",
        "external_id": "fr-001",
        "title": "Ingénieur DevOps",
    },
}

_ADZUNA_CANDIDATE = {
    "provider": "adzuna_uk",
    "external_id": "uk-001",
    "source_kind": "job",
    "title": "DevOps Engineer",
    "company_name": "CloudBase Ltd",
    "description": "Build and maintain CI/CD pipelines and K8s.",
    "location": "London",
    "country": "GB",
    "language": "en",
    "source_url": "https://example.com/uk-001",
    "source_published_at": "2025-07-01T00:00:00+00:00",
    "contract_type": "permanent",
    "remote_type": "hybrid",
    "budget_min": None,
    "budget_max": None,
    "budget_currency": None,
    "tags": ["devops", "kubernetes", "ci/cd"],
    "raw_payload": {
        "provider": "adzuna_uk",
        "external_id": "uk-001",
        "title": "DevOps Engineer",
    },
}

_FREELANCER_CANDIDATE = {
    "provider": "freelancer",
    "external_id": "fl-001",
    "source_kind": "freelance_project",
    "title": "Kubernetes Cluster Setup and Migration",
    "company_name": "GlobalTech GmbH",
    "description": "Set up a production-grade Kubernetes cluster.",
    "location": "Remote",
    "country": "GLOBAL",
    "language": "en",
    "source_url": "https://example.com/fl-001",
    "source_published_at": "2025-08-01T00:00:00+00:00",
    "contract_type": "project",
    "remote_type": "remote",
    "budget_min": 3000.0,
    "budget_max": 8000.0,
    "budget_currency": "EUR",
    "tags": ["kubernetes", "devops", "migration", "cloud"],
    "raw_payload": {
        "provider": "freelancer",
        "external_id": "fl-001",
        "title": "Kubernetes Cluster Setup",
    },
}


def _count(db: Session, model) -> int:
    return len(db.query(model).all())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImportFranceTravail:
    """Import a france_travail candidate."""

    def test_creates_source_record_company_opportunity(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_source_record"] is True
        assert data["created_company"] is True
        assert data["created_opportunity"] is True
        assert data["duplicate_detected"] is False

        assert _count(db_session, SourceRecord) == 1
        assert _count(db_session, Company) == 1
        assert _count(db_session, Opportunity) == 1
        assert _count(db_session, MessageDraft) == 0
        assert _count(db_session, FollowUp) == 0
        assert _count(db_session, ComplianceEvent) == 0

    def test_source_type_france_travail(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        sr = db_session.query(SourceRecord).first()
        assert sr.source_type == SourceType.france_travail

        opp = db_session.query(Opportunity).first()
        assert opp.source == SourceType.france_travail

    def test_language_fr(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.language == "fr"


class TestImportAdzunaUk:
    """Import an adzuna_uk candidate."""

    def test_creates_all_records(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_ADZUNA_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_source_record"] is True
        assert data["created_company"] is True
        assert data["created_opportunity"] is True
        assert data["duplicate_detected"] is False

        assert _count(db_session, SourceRecord) == 1

    def test_source_type_other(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_ADZUNA_CANDIDATE,
        )
        assert resp.status_code == 200
        sr = db_session.query(SourceRecord).first()
        assert sr.source_type == SourceType.other

        opp = db_session.query(Opportunity).first()
        assert opp.source == SourceType.other

    def test_language_en(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_ADZUNA_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.language == "en"


class TestImportFreelancer:
    """Import a freelancer candidate with budget fields."""

    def test_creates_all_records(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FREELANCER_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_source_record"] is True
        assert data["created_company"] is True
        assert data["created_opportunity"] is True

        assert _count(db_session, SourceRecord) == 1

    def test_notes_contain_budget(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FREELANCER_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.notes is not None
        assert "provider=freelancer" in opp.notes
        assert "external_id=fl-001" in opp.notes
        assert "source_kind=freelance_project" in opp.notes
        assert "budget_min=3000.0 EUR" in opp.notes
        assert "budget_max=8000.0 EUR" in opp.notes
        assert "country=GLOBAL" in opp.notes
        assert "contract_type=project" in opp.notes
        assert "remote_type=remote" in opp.notes

    def test_opportunity_type_devops_cloud(self, client, db_session):
        """Kubernetes + devops keywords in title/tags map to devops_cloud."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FREELANCER_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.opportunity_type == OpportunityType.devops_cloud


class TestDuplicatePrevention:
    """Importing the same candidate twice."""

    def test_duplicate_does_not_create_second_source_record(self, client, db_session):
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["duplicate_detected"] is True

        assert _count(db_session, SourceRecord) == 1
        assert _count(db_session, Opportunity) == 1
        assert _count(db_session, Company) == 1

    def test_duplicate_returns_existing_opportunity(self, client, db_session):
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp1.status_code == 200
        opp1_id = resp1.json()["opportunity"]["id"]

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp2.status_code == 200
        opp2_id = resp2.json()["opportunity"]["id"]

        assert opp2_id == opp1_id

    def test_duplicate_flags_no_new_records(self, client, db_session):
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["created_source_record"] is False
        assert data2["created_company"] is False
        assert data2["created_opportunity"] is False
        assert data2["duplicate_detected"] is True


class TestCompanyReuse:
    """Importing candidates with the same company name reuses the company."""

    def test_reuses_existing_company_same_name_country(self, client, db_session):
        payload_1 = {**_FT_CANDIDATE, "external_id": "fr-001"}
        payload_2 = {**_FT_CANDIDATE, "external_id": "fr-002", "title": "Architecte Cloud"}

        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload_1,
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload_2,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["created_company"] is False

        assert _count(db_session, Company) == 1

    def test_fallback_company_name_when_missing(self, client, db_session):
        payload = {**_FT_CANDIDATE, "company_name": None}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 200
        company = db_session.query(Company).first()
        assert company is not None
        assert "Unknown External Company" in company.name
        assert "france_travail" in company.name


class TestValidation:
    """Input validation for the import endpoint."""

    def test_unknown_provider_returns_400(self, client):
        payload = {**_FT_CANDIDATE, "provider": "non_existent"}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "non_existent" in detail


class TestSourceRecordRawPayload:
    """SourceRecord stores the raw payload from the candidate."""

    def test_raw_payload_contains_provider_external_id_title(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        sr = db_session.query(SourceRecord).first()
        assert sr.raw_payload is not None
        assert sr.raw_payload.get("provider") == "france_travail"
        assert sr.raw_payload.get("external_id") == "fr-001"
        assert "Ingénieur" in sr.raw_payload.get("title", "")


class TestOpportunityNotes:
    """Opportunity notes contain provenance metadata."""

    def test_notes_contain_provider_and_external_id(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.notes is not None
        assert "provider=france_travail" in opp.notes
        assert "external_id=fr-001" in opp.notes


class TestNoSideEffects:
    """Import creates only SourceRecord, Company, Opportunity — nothing else."""

    def test_no_message_draft_created(self, client, db_session):
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert _count(db_session, MessageDraft) == 0

    def test_no_follow_up_created(self, client, db_session):
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert _count(db_session, FollowUp) == 0

    def test_no_compliance_event_created(self, client, db_session):
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert _count(db_session, ComplianceEvent) == 0

    def test_no_side_effects_for_uk_provider(self, client, db_session):
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_ADZUNA_CANDIDATE,
        )
        assert _count(db_session, MessageDraft) == 0
        assert _count(db_session, FollowUp) == 0
        assert _count(db_session, ComplianceEvent) == 0

    def test_no_side_effects_for_freelancer(self, client, db_session):
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FREELANCER_CANDIDATE,
        )
        assert _count(db_session, MessageDraft) == 0
        assert _count(db_session, FollowUp) == 0
        assert _count(db_session, ComplianceEvent) == 0


class TestOpportunityTypeClassification:
    """Verify opportunity_type classification based on content."""

    def test_devops_keyword_maps_to_devops_cloud(self, client, db_session):
        payload = {**_FT_CANDIDATE, "tags": ["devops"]}
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        opp = db_session.query(Opportunity).first()
        assert opp.opportunity_type == OpportunityType.devops_cloud

    def test_non_devops_content_maps_to_other(self, client, db_session):
        payload = {
            **_FT_CANDIDATE,
            "title": "Comptable",
            "description": "Gestion comptable et financière de l'entreprise.",
            "tags": ["comptabilite", "finance"],
        }
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        opp = db_session.query(Opportunity).first()
        assert opp.opportunity_type == OpportunityType.other

    def test_freelance_project_without_devops_is_other(self, client, db_session):
        payload = {
            **_FREELANCER_CANDIDATE,
            "external_id": "fl-999",
            "title": "Rédaction de contenu",
            "description": "Rédaction d'articles et contenu web.",
            "tags": ["writing", "content"],
        }
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        opp = db_session.query(Opportunity).first()
        assert opp.opportunity_type == OpportunityType.other


class TestResponseSchema:
    """Verify response includes all expected fields."""

    def test_response_has_all_fields(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "source_record" in data
        assert "company" in data
        assert "opportunity" in data
        assert "created_source_record" in data
        assert "created_company" in data
        assert "created_opportunity" in data
        assert "duplicate_detected" in data
        assert "message" in data

    def test_response_includes_ids(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_record"].get("id") is not None
        assert data["company"].get("id") is not None
        assert data["opportunity"].get("id") is not None


class TestLanguageDefault:
    """Verify language fallback behavior per provider."""

    def test_france_travail_defaults_to_fr_when_empty(self, client, db_session):
        payload = {**_FT_CANDIDATE, "language": ""}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.language == "fr"

    def test_adzuna_uk_defaults_to_en_when_empty(self, client, db_session):
        payload = {**_ADZUNA_CANDIDATE, "language": ""}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.language == "en"


class TestImportReadOnlyOperations:
    """Verify that Phase 9A search endpoints remain read-only after Phase 9B changes."""

    def test_providers_still_read_only(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200

    def test_search_still_read_only(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
