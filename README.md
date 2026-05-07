# SORIA AI Prospecting Platform

[![CI](https://github.com/ben-edu/soria-ai-prospecting-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/ben-edu/soria-ai-prospecting-platform/actions/workflows/ci.yml)

SORIA is an IT services, cloud, cybersecurity, DevOps and training structure.

This platform helps SORIA discover, qualify, score, prepare and track opportunities across multiple domains:
- Training/formation
- DevOps and cloud clients
- Freelance missions
- Job opportunities (later)
- SOC/security opportunities (later)
- Academy/Moodle learning platform integration

## Core Principle

**The platform must never send uncontrolled automated messages.**
Every generated external message requires human validation before sending.

## Project Structure

```
soria-ai-prospecting-platform/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── core/      # Configuration, database, enums
│   │   ├── models/    # SQLModel database models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── api/       # API routes
│   │   ├── services/  # Business logic
│   │   └── repositories/  # Data access layer
│   ├── alembic/       # Database migrations
│   └── scripts/       # Maintenance scripts
├── docs/              # Documentation
├── kubernetes/        # Kubernetes manifests (planned)
└── README.md
```

## Local Development

### Prerequisites

- Python 3.12+ (see `.python-version`)
- PostgreSQL database
- uv (Python package manager)
- Docker & Docker Compose (optional, for local PostgreSQL)

### Setup

```bash
cd backend

# Create environment file
cp .env.example .env
# Edit .env with your local database URL

# [Option A] Start PostgreSQL via Docker
docker compose up -d postgres

# [Option B] Or use your own PostgreSQL instance
# Point DATABASE_URL in .env to your instance

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Seed initial data
uv run python -m app.scripts.seed_initial_data

# Run tests
uv run pytest

# Start development server
uv run uvicorn app.main:app --reload --port 8000
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | SORIA AI Prospecting Platform |
| `APP_ENV` | Environment (local/staging/prod) | local |
| `API_V1_PREFIX` | API version prefix | /api/v1 |
| `DATABASE_URL` | PostgreSQL connection string | postgresql+psycopg://soria:soria@localhost:5432/soria_prospecting |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000,http://localhost:8000 |
| `SECRET_KEY` | Application secret key | change-me |
| `LOG_LEVEL` | Logging level | INFO |
| `AI_DRAFT_PROVIDER` | AI provider for message draft generation | mock_ai |
| `AI_DRAFT_PROMPT_PROFILE` | Prompt profile identifier | prospecting_fr_v1 |
| `AI_DRAFT_MODEL_NAME` | Model name reported in audit metadata | mock-soria-v1 |
| `AI_DRAFT_PROMPT_VERSION` | Prompt version reported in audit metadata | ai-draft-v1 |

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1

# Check current state
uv run alembic current
```

### Seed Data

```bash
uv run python -m app.scripts.seed_initial_data
```

### MessageDraft Workflow

Message drafts follow a controlled human-validation lifecycle:

- **draft** &rarr; submit-review &rarr; **needs_review** &rarr; approve &rarr; **approved** &rarr; mark-sent-manually &rarr; **sent_manually**
- **rejected** &rarr; submit-review &rarr; **needs_review** (re-submit after revision)

Endpoints: `GET/POST /api/v1/message-drafts`, `GET/PATCH /api/v1/message-drafts/{id}`, workflow actions via `/submit-review`, `/approve`, `/reject`, `/mark-sent-manually`.

See [AI-Assisted Message Workflow](docs/phase-8-ai-assisted-message-workflow.md) for documentation of the AI draft generation pipeline (preview, generate, regenerate, diagnostics, provider architecture, audit metadata).

### API Health

```http
GET /api/v1/health
```

Response:
```json
{
  "status": "ok",
  "app": "SORIA AI Prospecting Platform"
}
```

## Kubernetes Deployment

Kubernetes manifests are planned but not part of this initial bootstrap run. See `kubernetes/README.md`.

## License

Proprietary — SORIA.
