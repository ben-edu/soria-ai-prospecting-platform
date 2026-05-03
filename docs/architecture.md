# Architecture

## System Overview

SORIA AI Prospecting Platform is designed as a modular, API-first backend service.

### Layers

1. **API Layer** (FastAPI routers) — HTTP endpoints, validation, routing
2. **Service Layer** — Business logic, scoring, message generation (future)
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

The platform is designed to never send automated external messages. Every message draft requires explicit human approval before it can be sent.

## Future Integrations

- LLM-based opportunity scoring and message generation
- External data enrichment (Hunter, Dropcontact)
- Email sending via SMTP provider
- LinkedIn automation (manual-assisted)
- OpenProject work package integration
- Academy/Moodle API integration
