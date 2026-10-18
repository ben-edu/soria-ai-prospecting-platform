# MVCS-3 B2B pilot alignment

This repository keeps its existing CRM and human-in-the-loop message workflow.
MVCS-3 adds a bounded B2B qualification profile; it does not add a crawler or
automatic sender.

## Pilot record contract

A first-pilot record is a `devops_cloud` opportunity curated from `manual`,
`company_website`, or `linkedin_manual` public evidence.

- `description`: factual summary of the observed public signal.
- `source_url`: attributable evidence URL.
- `source_published_at`: public signal date when known.
- `detected_need`: must be written explicitly as a hypothesis, never as a known internal fact.
- `offer_id` / `recommended_landing_page`: assigned by MVCS B2B qualification.

A job opening is a public capacity signal only. It is not evidence that the
company wants an external provider.

## Qualification

`POST /api/v1/b2b/opportunities/{id}/qualify`

Scoring version: `mvcs3-b2b-v1`.

- ICP fit: 0-35
- public-signal relevance/freshness: 0-30
- offer / pain-hypothesis fit: 0-20
- contactability: 0-10
- evidence quality: 0-5
- pilot threshold: 70

The result is stored through the existing `OpportunityScore` model with the
breakdown/reasons retained in JSON. Legacy `/opportunities/{id}/score` behavior
is unchanged.

## Productised offers

The deployment seed runs `python -m app.scripts.seed_mvcs_b2b` after the legacy
seed and idempotently synchronizes these offers without deleting legacy or
Academy catalog entries:

- Diagnostic déploiement & infrastructure
- Industrialisation des déploiements
- Fiabilité de production & exploitation

The exact production landing URLs are under `https://soria-ai.fr/solutions/`.

## Draft safety

Curated B2B `devops_cloud` records use the SORIA-first prompt profile
`soria_b2b_prospecting_fr_v1` / `mvcs3-b2b-v1`. The prompt requires strict
separation between observed public facts and unverified pain hypotheses and
forbids invented clients, results, team size, partnerships, SLA or purchase
intent.

Job/freelance modes keep their existing Behnam-centric prompt context.

All generated messages remain drafts. The existing lifecycle stays:

`draft -> needs_review -> approved -> sent_manually`

No external-source live-mode change and no unattended message delivery are
part of MVCS-3B.
