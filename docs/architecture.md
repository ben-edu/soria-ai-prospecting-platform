# Architecture

## System Overview

SORIA AI Prospecting Platform is designed as a modular, API-first backend service.

### Layers

1. **API Layer** (FastAPI routers) — HTTP endpoints, validation, routing
2. **Service Layer** — Business logic, scoring, AI prompt builder (`ai_prompt_builder.py`), AI provider abstraction with registry and diagnostics (`ai_providers.py`), AI message generation orchestrator with output validation and safe failure handling (`ai_message_generation.py`), workflow events (`workflow_events.py`)
3. **Repository Layer** — Data access abstraction (future use)
4. **Model Layer** — SQLModel ORM models, enums, database schema

### Traffic Flow (planned)

```
Internet
  → OPNsense (edge firewall + HAProxy + TLS termination)
  → Kubernetes ingress (Traefik)
  → FastAPI backend
  → PostgreSQL
```

### Key Design Decisions

- **SQLModel** combines Pydantic and SQLAlchemy for type-safe models
- **Alembic** handles schema migrations
- **Pydantic Settings** manages configuration via environment
- **UUID primary keys** for distributed compatibility
- **JSON fields** for flexible metadata storage
- **Timezone-aware datetimes** throughout

### Human-in-the-Loop

The platform is designed to never send automated external messages. Every message draft requires explicit human approval before it can be sent. The AI-assisted draft generation pipeline follows this principle: preview is read-only, generate creates a draft in `draft` status, and sending is only recorded manually after explicit human approval.

### AI Provider Abstraction

The platform includes a provider abstraction layer (`ai_providers.py`) with a registered provider registry, resolver, and custom exception hierarchy. The current implementation uses `mock_ai`, a deterministic mock provider for French prospecting email generation. No external AI API is currently called — the abstraction exists to enable future real provider integration (OpenAI, Claude, etc.) without changing the orchestration or endpoint code.

### Diagnostics and Safe Failure

A read-only diagnostics endpoint (`GET /opportunities/ai-diagnostics/provider`) reports configured provider, model, prompt profile, prompt version, and provider availability. Safe failure handling ensures that regeneration archives old drafts only after successful generation, preventing data loss on provider failure.

## Future Integrations

- Real external AI provider integration (OpenAI/Claude)
- LLM-based opportunity scoring and qualification
- External data enrichment (Hunter, Dropcontact)
- Email sending via SMTP provider
- LinkedIn automation (manual-assisted)
- OpenProject work package integration
- Academy/Moodle API integration
- France Travail API integration
