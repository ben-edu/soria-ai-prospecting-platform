"""Idempotently persist and qualify the human-approved MVCS-3C shortlist.

This script is deliberately bounded to the ten companies approved on 2026-10-18.
It stores public company/opportunity evidence, keeps potential pain explicitly
hypothetical, creates no MessageDraft/FollowUp/Interaction rows, and does not
send or trigger any external communication.

Decision-maker names remain evidence in notes only. Contact rows are deferred
until MVCS-3D, when a specific recipient is re-verified for a reviewed draft.
"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.database import engine
from app.core.enums import (
    CompanyStatus,
    CompanyType,
    OpportunityPriority,
    OpportunityStatus,
    OpportunityType,
    SourceType,
)
from app.models.company import Company
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.models.opportunity_score import OpportunityScore
from app.scripts.seed_mvcs_b2b import sync_mvcs_b2b_catalog
from app.services.mvcs_b2b import (
    B2B_QUALIFICATION_THRESHOLD,
    B2B_SCORING_VERSION,
    qualify_mvcs_b2b,
    select_mvcs_offer_slug,
)

IMPORT_BATCH = "mvcs3c-approved-2026-10-18"

EARLY_OPPORTUNITY_STATUSES = {
    OpportunityStatus.new,
    OpportunityStatus.imported_pending_review,
    OpportunityStatus.to_analyze,
    OpportunityStatus.scored,
    OpportunityStatus.interesting,
}

EDITABLE_COMPANY_STATUSES = {
    CompanyStatus.new,
    CompanyStatus.to_review,
    CompanyStatus.qualified,
}


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


APPROVED_SHORTLIST = [
    {
        "name": "Shotgun",
        "slug": "mvcs3c-shotgun",
        "website_url": "https://shotgun.live/",
        "domain": "shotgun.live",
        "company_type": CompanyType.startup,
        "sector": "SaaS software online ticketing platform",
        "city": "Paris",
        "company_source_url": "https://pro.shotgun.live/fr/a-propos",
        "decision_maker": "Lucas Gerard — Co-founder / CTO",
        "decision_maker_source": "https://wellfound.com/company/shotgun/people",
        "title": "SRE production reliability scalability observability",
        "description": (
            "Public signal: Shotgun states that it is recruiting its first dedicated "
            "SRE to build production-grade cloud foundations for scalability, "
            "observability, security and developer tooling as the live product grows."
        ),
        "detected_need": (
            "Hypothèse: a bounded production/reliability review or implementation "
            "support could complement the transition toward a first dedicated SRE "
            "function; vendor intent is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://www.welcometothejungle.com/fr/companies/shotgun/jobs/"
            "site-reliability-engineer-devops"
        ),
        "source_published_at": None,
    },
    {
        "name": "Parallel",
        "slug": "mvcs3c-parallel",
        "website_url": "https://www.beparallel.com/",
        "domain": "beparallel.com",
        "company_type": CompanyType.startup,
        "sector": "SaaS software health AI platform",
        "city": "Paris",
        "company_source_url": "https://www.beparallel.com/fr/",
        "decision_maker": "Chris — Co-founder (public first-name evidence only)",
        "decision_maker_source": "https://www.welcometothejungle.com/fr/companies/kiosk",
        "title": "SRE production reliability multi-cloud observability",
        "description": (
            "Public signal: Parallel describes its first/only DevOps-SRE position "
            "across AWS, GCP, Azure, hospital on-premise deployments, CI/CD, "
            "observability, security and reliability for a live medical-coding product."
        ),
        "detected_need": (
            "Hypothèse: a bounded reliability/production review could help de-risk "
            "the initial SRE foundation across multi-cloud and hospital on-premise "
            "environments; vendor intent is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://jobs.ashbyhq.com/beparallel/"
            "ad3a6d29-89da-4b4e-8a2c-51fd21a1b638"
        ),
        "source_published_at": None,
    },
    {
        "name": "amo",
        "slug": "mvcs3c-amo",
        "website_url": "https://amo.co/",
        "domain": "amo.co",
        "company_type": CompanyType.startup,
        "sector": "software mobile social online product",
        "city": "Paris",
        "company_source_url": "https://amo.co/about/",
        "decision_maker": "Antoine Martin — Co-founder",
        "decision_maker_source": (
            "https://techcrunch.com/2023/11/19/"
            "with-amo-the-founder-of-zenly-wants-to-make-social-apps-social-again/"
        ),
        "title": "Lead SRE production reliability scalability automation",
        "description": (
            "Public signal: amo is recruiting a Lead SRE to own the long-term "
            "infrastructure roadmap and keep live systems reliable, scalable and secure "
            "while global traffic grows."
        ),
        "detected_need": (
            "Hypothèse: a bounded reliability/production assessment could help "
            "prioritise operational safeguards while traffic and infrastructure "
            "ownership scale; vendor intent is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://jobs.ashbyhq.com/amo/"
            "11ad3081-f6a0-4150-8681-4246d3cfa3e1/"
        ),
        "source_published_at": None,
    },
    {
        "name": "My Job Glasses",
        "slug": "mvcs3c-my-job-glasses",
        "website_url": "https://www.myjobglasses.com/",
        "domain": "myjobglasses.com",
        "company_type": CompanyType.startup,
        "sector": "software EdTech online platform",
        "city": "Paris",
        "company_source_url": "https://www.myjobglasses.com/qui-sommes-nous-my-job-glasses/",
        "decision_maker": "Émilie Korchia — Founder / CEO",
        "decision_maker_source": "https://www.myjobglasses.com/qui-sommes-nous-my-job-glasses/",
        "title": "Senior DevOps SRE production reliability observability scaling",
        "description": (
            "Public signal: My Job Glasses states that it is internalising DevOps "
            "expertise and strengthening reliability, security, scaling, production "
            "observability, incidents and SLO/RTO/RPO practices during growth."
        ),
        "detected_need": (
            "Hypothèse: a bounded reliability review could support prioritisation "
            "while DevOps expertise is being internalised; the hiring signal is not "
            "proof of external-provider demand."
        ),
        "source": SourceType.manual,
        "source_url": "https://www.jobijoba.com/fr/annonce/54/db944ffe495ce725e6968ea000dd7b35",
        "source_published_at": _dt(2026, 9, 15),
    },
    {
        "name": "XXII GROUP",
        "slug": "mvcs3c-xxii-group",
        "website_url": "https://www.xxiiai.com/",
        "domain": "xxiiai.com",
        "company_type": CompanyType.it_company,
        "sector": "software AI platform computer vision",
        "city": "Puteaux",
        "company_source_url": "https://www.xxiiai.com/",
        "decision_maker": "William Eldin — Founder / CEO",
        "decision_maker_source": (
            "https://xxii-group.welcomekit.co/jobs/senior-platform-engineer-f-h_puteaux"
        ),
        "title": "CI/CD deployment Kubernetes GitLab CI platform automation",
        "description": (
            "Public signal: XXII describes senior platform/operations work across the "
            "CORE edge/on-premise and cloud deployment chain with Kubernetes/k0s, "
            "Ansible, GitLab CI, Prometheus/Grafana and infrastructure evolution."
        ),
        "detected_need": (
            "Hypothèse: a bounded deployment-industrialisation review could help "
            "reduce friction and standardise delivery across distributed edge/customer "
            "sites; vendor intent is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://xxii-group.welcomekit.co/jobs/"
            "senior-platform-engineer-f-h_puteaux"
        ),
        "source_published_at": None,
    },
    {
        "name": "ModuloTech",
        "slug": "mvcs3c-modulotech",
        "website_url": "https://www.modulotech.fr/",
        "domain": "modulotech.fr",
        "company_type": CompanyType.it_company,
        "sector": "software SaaS mobile field-service platform",
        "city": "Issy-les-Moulineaux",
        "company_source_url": "https://www.modulotech.fr/page-kaze.html",
        "decision_maker": "Leadership evidence public; recipient not yet re-verified",
        "decision_maker_source": "https://www.modulotech.fr/",
        "title": "SRE production reliability observability recovery Kubernetes",
        "description": (
            "Public signal: ModuloTech is strengthening SRE capability around "
            "production Kubernetes, database migration/rollback, AWS/IaC, reliability, "
            "observability and disaster recovery as product usage grows."
        ),
        "detected_need": (
            "Hypothèse: a bounded reliability/production review could help prioritise "
            "resilience and migration risks while SRE capacity expands; vendor intent "
            "is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://modulotech.welcomekit.co/jobs/"
            "site-reliability-engineer-h-f-x_issy-les-moulineaux"
        ),
        "source_published_at": None,
    },
    {
        "name": "Implicity",
        "slug": "mvcs3c-implicity",
        "website_url": "https://implicity.com/",
        "domain": "implicity.com",
        "company_type": CompanyType.startup,
        "sector": "software health AI online monitoring platform",
        "city": "Paris",
        "company_source_url": "https://implicity.com/",
        "decision_maker": "Louay — CTO; Cyrille — DevOps & Infrastructure Engineering Manager",
        "decision_maker_source": "https://implicity.com/careers/",
        "title": "Senior SRE production reliability multi-cloud observability",
        "description": (
            "Public signal: Implicity is recruiting a Senior SRE to keep its live "
            "regulated remote-monitoring platform reliable while scaling toward the US "
            "and a multi-cloud infrastructure transformation."
        ),
        "detected_need": (
            "Hypothèse: a bounded reliability/production assessment could provide "
            "additional focused capacity during the multi-cloud and scaling transition; "
            "vendor intent is not established."
        ),
        "source": SourceType.company_website,
        "source_url": "https://implicity.teamtailor.com/jobs/8556697-senior-site-reliability-engineer-sre",
        "source_published_at": _dt(2026, 10, 16),
    },
    {
        "name": "TrustBuilder",
        "slug": "mvcs3c-trustbuilder",
        "website_url": "https://trustbuilder.com/",
        "domain": "trustbuilder.com",
        "company_type": CompanyType.it_company,
        "sector": "software SaaS cybersecurity identity platform",
        "city": "Paris",
        "company_source_url": "https://trustbuilder.com/",
        "decision_maker": "Chakib Benyakhlef — Senior R&D / engineering leadership",
        "decision_maker_source": (
            "https://www.welcometothejungle.com/en/companies/inwebo-technologies/team-1"
        ),
        "title": "CI/CD deployment automation Terraform Ansible Docker",
        "description": (
            "Public signal: TrustBuilder describes DevOps work covering GCP platforms, "
            "internal/client CI/CD pipelines and infrastructure/deployment automation "
            "with Terraform, Ansible and Docker for a live identity-security SaaS."
        ),
        "detected_need": (
            "Hypothèse: a bounded deployment-industrialisation review could identify "
            "standardisation or developer-delivery improvements as the platform scales; "
            "an existing DevOps organisation means external need is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://www.welcometothejungle.com/fr/companies/inwebo-technologies/jobs/"
            "devops-engineer_paris_TRUST_LWxb94G"
        ),
        "source_published_at": None,
    },
    {
        "name": "ADLIN Science",
        "slug": "mvcs3c-adlin-science",
        "website_url": "https://www.adlin-science.com/",
        "domain": "adlin-science.com",
        "company_type": CompanyType.startup,
        "sector": "software health-data platform SaaS",
        "city": "Évry",
        "company_source_url": "https://www.adlin-science.com/",
        "decision_maker": "Julien Gabry — CTO; Paul Rinaudo — CEO",
        "decision_maker_source": "https://www.adlin-science.com/decouvrez-adlin/equipe",
        "title": "SRE production reliability monitoring recovery backup Kubernetes",
        "description": (
            "Public signal: ADLIN describes active DevOps work spanning GitLab CI/CD, "
            "Docker/Kubernetes, dev-staging-production separation, monitoring, "
            "observability, automated incident detection, disaster recovery and backups."
        ),
        "detected_need": (
            "Hypothèse: a bounded reliability/recovery review could complement the "
            "platform's growing DevOps maturity and help prioritise operational controls; "
            "vendor intent is not established."
        ),
        "source": SourceType.linkedin_manual,
        "source_url": (
            "https://fr.linkedin.com/jobs/view/"
            "ing%C3%A9nieur-devops-senior-at-adlin-science-4343562827"
        ),
        "source_published_at": None,
    },
    {
        "name": "Stoïk",
        "slug": "mvcs3c-stoik",
        "website_url": "https://www.stoik.com/",
        "domain": "stoik.com",
        "company_type": CompanyType.startup,
        "sector": "software SaaS cybersecurity InsurTech platform",
        "city": "Paris",
        "company_source_url": "https://www.stoik.com/",
        "decision_maker": "Nicolas Sayer — CPTO / Directeur Technique",
        "decision_maker_source": (
            "https://www.welcometothejungle.com/fr/companies/stoik/team-1"
        ),
        "title": "DevOps cloud Terraform Kubernetes AWS platform evolution",
        "description": (
            "Public signal: Stoïk is strengthening DevOps/platform engineering capacity "
            "around AWS, Terraform and Kubernetes while operating a live cyber-insurance "
            "and security-software platform."
        ),
        "detected_need": (
            "Hypothèse: a bounded deployment and infrastructure diagnostic could help "
            "prioritise platform-evolution topics before any implementation scope is "
            "assumed; vendor intent is not established."
        ),
        "source": SourceType.manual,
        "source_url": (
            "https://www.welcometothejungle.com/fr/companies/stoik/jobs/"
            "devops_paris_STOK_54Z7dQD"
        ),
        "source_published_at": None,
    },
]


def build_candidate_models(candidate: dict) -> tuple[Company, Opportunity]:
    company = Company(
        name=candidate["name"],
        slug=candidate["slug"],
        website_url=candidate["website_url"],
        domain=candidate["domain"],
        company_type=candidate["company_type"],
        sector=candidate["sector"],
        city=candidate["city"],
        country="France",
        source=SourceType.manual,
        source_url=candidate["company_source_url"],
        notes=(
            f"{IMPORT_BATCH}; human shortlist approved 2026-10-18; "
            f"vendor_intent=not_established; decision-maker evidence: "
            f"{candidate['decision_maker']} — {candidate['decision_maker_source']}"
        ),
        status=CompanyStatus.to_review,
    )
    opportunity = Opportunity(
        company_id=company.id,
        title=candidate["title"],
        opportunity_type=OpportunityType.devops_cloud,
        description=candidate["description"],
        detected_need=candidate["detected_need"],
        source=candidate["source"],
        source_url=candidate["source_url"],
        source_published_at=candidate["source_published_at"],
        location=f"{candidate['city']}, France",
        language="fr",
        status=OpportunityStatus.imported_pending_review,
        priority=OpportunityPriority.high,
        notes=(
            f"{IMPORT_BATCH}; human shortlist approved 2026-10-18; "
            "vendor_intent=not_established; no external message authorised; "
            f"live-product evidence: {candidate['company_source_url']}; "
            f"decision-maker evidence: {candidate['decision_maker']} — "
            f"{candidate['decision_maker_source']}"
        ),
    )
    return company, opportunity


def _apply_company_facts(company: Company, candidate: dict) -> None:
    company.name = candidate["name"]
    company.website_url = candidate["website_url"]
    company.domain = candidate["domain"]
    company.company_type = candidate["company_type"]
    company.sector = candidate["sector"]
    company.city = candidate["city"]
    company.country = "France"
    company.source = SourceType.manual
    company.source_url = candidate["company_source_url"]
    if IMPORT_BATCH not in (company.notes or ""):
        company.notes = (
            ((company.notes or "").strip() + "\n")
            + f"{IMPORT_BATCH}; human shortlist approved 2026-10-18; "
            + "vendor_intent=not_established; decision-maker evidence: "
            + f"{candidate['decision_maker']} — {candidate['decision_maker_source']}"
        ).strip()


def _apply_opportunity_facts(opportunity: Opportunity, candidate: dict) -> None:
    opportunity.title = candidate["title"]
    opportunity.opportunity_type = OpportunityType.devops_cloud
    opportunity.description = candidate["description"]
    opportunity.detected_need = candidate["detected_need"]
    opportunity.source = candidate["source"]
    opportunity.source_url = candidate["source_url"]
    opportunity.source_published_at = candidate["source_published_at"]
    opportunity.location = f"{candidate['city']}, France"
    opportunity.language = "fr"
    opportunity.priority = OpportunityPriority.high
    if IMPORT_BATCH not in (opportunity.notes or ""):
        opportunity.notes = (
            ((opportunity.notes or "").strip() + "\n")
            + f"{IMPORT_BATCH}; human shortlist approved 2026-10-18; "
            + "vendor_intent=not_established; no external message authorised; "
            + f"live-product evidence: {candidate['company_source_url']}; "
            + f"decision-maker evidence: {candidate['decision_maker']} — "
            + f"{candidate['decision_maker_source']}"
        ).strip()


def sync_and_qualify_approved_shortlist(session: Session) -> list[dict]:
    """Persist the approved shortlist once and return auditable qualification results."""

    sync_mvcs_b2b_catalog(session)
    session.flush()
    results: list[dict] = []

    for candidate in APPROVED_SHORTLIST:
        company = session.exec(
            select(Company).where(Company.slug == candidate["slug"])
        ).first()
        if company is None:
            company, _ = build_candidate_models(candidate)
            session.add(company)
            session.flush()
        elif company.status in EDITABLE_COMPANY_STATUSES:
            _apply_company_facts(company, candidate)
            session.add(company)
            session.flush()

        opportunity = session.exec(
            select(Opportunity).where(
                Opportunity.company_id == company.id,
                Opportunity.opportunity_type == OpportunityType.devops_cloud,
                Opportunity.source_url == candidate["source_url"],
            )
        ).first()

        if opportunity is None:
            _, opportunity = build_candidate_models(candidate)
            opportunity.company_id = company.id
            session.add(opportunity)
            session.flush()
        elif opportunity.status not in EARLY_OPPORTUNITY_STATUSES:
            results.append(
                {
                    "slug": candidate["slug"],
                    "status": "preserved-lifecycle",
                    "opportunity_id": str(opportunity.id),
                    "score": opportunity.score,
                }
            )
            continue
        else:
            _apply_opportunity_facts(opportunity, candidate)
            session.add(opportunity)
            session.flush()

        offer_slug = select_mvcs_offer_slug(opportunity)
        offer = session.exec(select(Offer).where(Offer.slug == offer_slug)).first()
        if offer is None or not offer.is_active:
            raise RuntimeError(f"Required active MVCS offer missing: {offer_slug}")

        qualification = qualify_mvcs_b2b(opportunity, company, None, offer)
        if not qualification["qualified"]:
            raise RuntimeError(
                f"Approved MVCS-3C candidate fell below threshold: "
                f"{candidate['name']}={qualification['score']}"
            )

        opportunity.offer_id = offer.id
        opportunity.recommended_landing_page = offer.landing_page_url
        opportunity.score = qualification["score"]
        opportunity.status = OpportunityStatus.interesting
        opportunity.next_action = (
            "Human shortlist approved. Re-verify one public decision-maker/recipient "
            "before preparing an MVCS-3D draft; no external send is authorised."
        )
        session.add(opportunity)

        if company.status in EDITABLE_COMPANY_STATUSES:
            company.status = CompanyStatus.qualified
            session.add(company)

        previous_score = session.exec(
            select(OpportunityScore)
            .where(
                OpportunityScore.opportunity_id == opportunity.id,
                OpportunityScore.scoring_version == B2B_SCORING_VERSION,
            )
            .order_by(OpportunityScore.created_at.desc())
        ).first()

        if previous_score is None or previous_score.total_score != qualification["score"]:
            session.add(
                OpportunityScore(
                    opportunity_id=opportunity.id,
                    total_score=qualification["score"],
                    business_score=qualification["score"],
                    reasons={
                        "breakdown": qualification["breakdown"],
                        "details": qualification["reasons"],
                        "threshold": B2B_QUALIFICATION_THRESHOLD,
                        "qualified": True,
                        "matched_offer_slug": offer.slug,
                        "import_batch": IMPORT_BATCH,
                        "human_shortlist_approved": "2026-10-18",
                        "vendor_intent": "not_established",
                    },
                    scoring_version=B2B_SCORING_VERSION,
                )
            )

        results.append(
            {
                "slug": candidate["slug"],
                "status": "qualified",
                "opportunity_id": str(opportunity.id),
                "score": qualification["score"],
                "offer_slug": offer.slug,
                "breakdown": qualification["breakdown"],
            }
        )

    session.commit()
    return results


def run() -> None:
    with Session(engine) as session:
        results = sync_and_qualify_approved_shortlist(session)

    qualified = [item for item in results if item["status"] == "qualified"]
    preserved = [item for item in results if item["status"] == "preserved-lifecycle"]
    print(
        f"MVCS-3C approved shortlist synchronized: {len(qualified)} qualified, "
        f"{len(preserved)} preserved lifecycle records."
    )
    for item in results:
        print(item)


if __name__ == "__main__":
    run()
