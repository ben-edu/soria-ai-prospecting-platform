"""Phase 14C — URL persistence, duplicate prevention, language detection.

Covers:
- Imported candidate keeps source_url when available
- Duplicate import by URL is blocked/reused
- Duplicate import by source_name + external_id is blocked when URL missing
- France Travail candidate without URL keeps external_id/provider reference
- language_hint detects English and French cases
- prompt_context includes language_hint
"""


class TestSourceUrlPersistence:
    """Imported candidates preserve source_url."""

    _ADZUNA_CANDIDATE = {
        "provider": "adzuna_uk",
        "external_id": "uk-test-url-001",
        "source_kind": "job",
        "title": "DevOps Engineer with URL",
        "description": "A great DevOps job with a source URL.",
        "country": "GB",
        "language": "en",
        "source_url": "https://www.adzuna.co.uk/jobs/uk-test-url-001",
        "tags": ["devops"],
        "raw_payload": {"id": "uk-test-url-001"},
    }

    _CANDIDATE_WITHOUT_URL = {
        "provider": "france_travail",
        "external_id": "fr-no-url-001",
        "source_kind": "job",
        "title": "Poste sans URL",
        "description": "Un poste sans URL source.",
        "country": "FR",
        "language": "fr",
        "source_url": None,
        "tags": ["devops"],
        "raw_payload": {"id": "fr-no-url-001"},
    }

    def test_adzuna_candidate_keeps_source_url(self, client):
        """Imported Adzuna candidate preserves source_url on all records."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._ADZUNA_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Opportunity should have the source_url
        opp = data["opportunity"]
        assert opp["source_url"] == "https://www.adzuna.co.uk/jobs/uk-test-url-001"

        # SourceRecord should have the source_url
        sr = data["source_record"]
        assert sr["source_url"] == "https://www.adzuna.co.uk/jobs/uk-test-url-001"

        assert data["duplicate_detected"] is False
        assert data["created_opportunity"] is True

    def test_france_travail_without_url_fallback_reference(self, client):
        """France Travail candidate without URL gets fallback via external_id."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._CANDIDATE_WITHOUT_URL,
        )
        assert resp.status_code == 200
        data = resp.json()

        opp = data["opportunity"]
        # source_url may be None or the France Travail fallback URL
        # The key is that the notes contain the external_id reference
        notes = opp.get("notes", "") or ""
        assert "external_id=fr-no-url-001" in notes
        assert "source_url=" in notes or "fallback_ref=" in notes

        sr = data["source_record"]
        assert sr["external_id"] == "fr-no-url-001"
        assert sr["source_name"] == "france_travail"


class TestDuplicatePreventionByUrl:
    """Duplicate import by URL is blocked/reused."""

    _CANDIDATE = {
        "provider": "adzuna_uk",
        "external_id": "uk-dup-url-001",
        "source_kind": "job",
        "title": "Duplicate by URL",
        "description": "Testing URL-based dedup.",
        "country": "GB",
        "language": "en",
        "source_url": "https://www.adzuna.co.uk/jobs/uk-dup-url-001",
        "tags": ["devops"],
        "raw_payload": {"id": "uk-dup-url-001"},
    }

    def test_first_import_succeeds(self, client):
        """First import creates records."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["duplicate_detected"] is False
        assert data["created_opportunity"] is True

    def test_second_import_by_same_url_blocked(self, client):
        """Second import with same URL returns duplicate_detected=True."""
        # First import
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._CANDIDATE,
        )

        # Second import (same URL, different external_id to prove URL check works)
        candidate2 = dict(self._CANDIDATE)
        candidate2["external_id"] = "uk-dup-url-002"
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=candidate2,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["duplicate_detected"] is True
        assert data["created_opportunity"] is False
        assert "source_url" in data["message"] or "Duplicate" in data["message"]


class TestDuplicatePreventionByExternalId:
    """Duplicate import by source_name + external_id when URL is missing."""

    _CANDIDATE = {
        "provider": "france_travail",
        "external_id": "fr-dup-extid-001",
        "source_kind": "job",
        "title": "Duplicate by External ID",
        "description": "Testing external_id-based dedup without URL.",
        "country": "FR",
        "language": "fr",
        "source_url": None,
        "tags": ["devops"],
        "raw_payload": {"id": "fr-dup-extid-001"},
    }

    def test_first_import_succeeds(self, client):
        """First import creates records."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["duplicate_detected"] is False

    def test_second_import_by_external_id_blocked(self, client):
        """Second import with same provider+external_id returns duplicate."""
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._CANDIDATE,
        )

        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["duplicate_detected"] is True
        assert data["created_opportunity"] is False


class TestLanguageHint:
    """language_hint detects English and French cases."""

    def test_infer_language_hint_english(self):
        """Strong English markers return 'en'."""
        from app.services.external_sources import infer_language_hint

        result = infer_language_hint(
            title="Senior DevOps Engineer",
            description="Join our team and work on cloud infrastructure. "
                        "We are looking for an experienced engineer.",
        )
        assert result == "en"

    def test_infer_language_hint_french(self):
        """Strong French markers return 'fr'."""
        from app.services.external_sources import infer_language_hint

        result = infer_language_hint(
            title="Ingénieur DevOps",
            description="Nous recherchons un ingénieur DevOps "
                        "pour rejoindre notre équipe.",
        )
        assert result == "fr"

    def test_infer_language_hint_french_source_country(self):
        """French source country defaults to 'fr'."""
        from app.services.external_sources import infer_language_hint

        result = infer_language_hint(
            title="Offre sans marqueurs forts",
            description="Description générique pour test",
            source_country="FR",
        )
        assert result == "fr"

    def test_infer_language_hint_english_overrides_french_country(self):
        """Very strong English signal overrides FR country default."""
        from app.services.external_sources import infer_language_hint

        result = infer_language_hint(
            title="Senior DevOps Engineer position available now",
            description="Join our team and work with the best engineers. "
                        "We are looking for an experienced professional. "
                        "This is a permanent full-time position with benefits.",
            source_country="FR",
        )
        assert result == "en"

    def test_infer_language_hint_unknown(self):
        """No clear markers return 'unknown'."""
        from app.services.external_sources import infer_language_hint

        result = infer_language_hint(
            title="",
            description="",
        )
        assert result == "unknown"

    def test_adzuna_uk_search_returns_english(self, client):
        """Adzuna UK mock candidates have en language."""
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["language"] == "en"

    def test_france_travail_search_returns_french(self, client):
        """France Travail mock candidates have fr language."""
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["language"] == "fr"


class TestPromptContextIncludesLanguageHint:
    """prompt_context includes language_hint."""

    def test_build_prompt_context_has_language_hint(self):
        """build_prompt_context returns language_hint in top-level and user_context."""
        from unittest.mock import MagicMock

        from app.services.ai_prompt_builder import build_prompt_context

        # Build a minimal Opportunity-like mock
        opp = MagicMock()
        opp.title = "Senior DevOps Engineer"
        opp.description = "Join our team to build cloud infrastructure."
        opp.detected_need = ""
        opp.recommended_landing_page = ""
        opp.opportunity_type = None

        context = build_prompt_context(opportunity=opp)

        # Top-level language_hint
        assert "language_hint" in context
        assert context["language_hint"] == "en"

        # user_context language_hint
        assert "language_hint" in context["user_context"]
        assert context["user_context"]["language_hint"] == "en"

    def test_build_prompt_context_french_detection(self):
        """French opportunity content gets language_hint=fr."""
        from unittest.mock import MagicMock

        from app.services.ai_prompt_builder import build_prompt_context

        opp = MagicMock()
        opp.title = "Ingénieur DevOps"
        opp.description = (
            "Nous recherchons un ingénieur DevOps expérimenté "
            "pour rejoindre notre équipe infrastructure."
        )
        opp.detected_need = ""
        opp.recommended_landing_page = ""
        opp.opportunity_type = None

        context = build_prompt_context(opportunity=opp)

        assert context["language_hint"] == "fr"
        assert context["user_context"]["language_hint"] == "fr"

    def test_build_prompt_context_unknown_detection(self):
        """Empty content gets language_hint=unknown."""
        from unittest.mock import MagicMock

        from app.services.ai_prompt_builder import build_prompt_context

        opp = MagicMock()
        opp.title = ""
        opp.description = ""
        opp.detected_need = ""
        opp.recommended_landing_page = ""
        opp.opportunity_type = None

        context = build_prompt_context(opportunity=opp)

        assert context["language_hint"] == "unknown"
        assert context["user_context"]["language_hint"] == "unknown"
