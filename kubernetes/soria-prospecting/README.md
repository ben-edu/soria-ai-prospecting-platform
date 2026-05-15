# SORIA Prospecting Platform — Kubernetes Deployment

## Namespace

All resources live in namespace `soria-prospecting`.

## Required Secrets (manual — not in Git)

Create the secret `soria-secrets` in namespace `soria-prospecting` with the following keys:

| Key                | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `POSTGRES_PASSWORD`| PostgreSQL password for user `soria`                                        |
| `DATABASE_URL`     | SQLAlchemy connection string (see format below)                             |
| `SECRET_KEY`       | FastAPI secret key for session/JWT signing                                  |

```bash
kubectl create secret generic soria-secrets \
  -n soria-prospecting \
  --from-literal=POSTGRES_PASSWORD='<your-password>' \
  --from-literal=DATABASE_URL='postgresql+psycopg://soria:<url-encoded-password>@postgres:5432/soria_prospecting' \
  --from-literal=SECRET_KEY='<your-secret-key>'
```

**DATABASE_URL format:**
```
postgresql+psycopg://soria:<url-encoded-password>@postgres:5432/soria_prospecting
```

## Required OAuth Proxy Secret (manual — not in Git)

The `soria-oauth-proxy` secret must exist in namespace `soria-prospecting` with the following keys:

| Key             | Description                                      |
|-----------------|--------------------------------------------------|
| `client-id`     | Keycloak OIDC client ID (`soria-cockpit`)        |
| `client-secret` | Keycloak OIDC client secret                      |
| `cookie-secret` | oauth2-proxy cookie encryption secret |

```bash
kubectl create secret generic soria-oauth-proxy \
  -n soria-prospecting \
  --from-literal=client-id='soria-cockpit' \
  --from-literal=client-secret='<your-client-secret>' \
  --from-literal=cookie-secret="$(openssl rand -base64 32 | tr -d '\n')"
```

## Required Image Pull Secret (manual — not in Git)

The `harbor-regcred` secret must exist in namespace `soria-prospecting` for pulling images from Harbor.
It can be copied from the `fastapi-platform` namespace if already configured:

```bash
kubectl get secret harbor-regcred -n fastapi-platform -o yaml \
  | sed 's/namespace: fastapi-platform/namespace: soria-prospecting/' \
  | kubectl apply -f -
```

## Jenkins Deploy Flow

The Jenkinsfile at the repository root implements a CI/CD pipeline:

1. **Quality gates** — type-check, lint, test, build
2. **Container build & push** — both backend and cockpit images to Harbor
3. **Kustomize tag update** — replaces `newTag` with the Git SHA
4. **Apply to cluster** — `kubectl apply -k overlays/prod`
5. **Migration job** — runs Alembic migrations + seed data
6. **Rollout & validation** — waits for deployments, runs health checks

Branch behavior:
- **main**: full pipeline including deploy
- **non-main**: build + test only (no Kubernetes apply)

## DNS / Host

Public ingress is configured for:

```
https://react-admin.behnam.fr
```

The Traefik ingress handles:
- `/api` → `soria-backend:8000`
- `/`   → `soria-cockpit:80`

Required external setup (outside this repo):
- Public DNS `react-admin.behnam.fr` pointing to the OVH edge
- OPNsense HAProxy + ACME for TLS (already in place)
- NodePort 32508 forwarding to Traefik

## Validation Commands

```bash
# Render manifests locally (after kustomize edit)
kubectl kustomize kubernetes/soria-prospecting/overlays/prod

# Check namespace resources
kubectl get pods,svc,ingress -n soria-prospecting

# Check rollout status
kubectl rollout status deployment/soria-backend -n soria-prospecting
kubectl rollout status deployment/soria-cockpit -n soria-prospecting

# Public health check
curl -fsS https://react-admin.behnam.fr/api/v1/health
```

## Resource Overview

| Resource              | Kind       | Replicas | Image Source        |
|-----------------------|------------|----------|---------------------|
| soria-postgres        | Deployment | 1        | postgres:16-alpine  |
| postgres              | Service    | —        | —                   |
| soria-backend         | Deployment | 1        | Harbor (FastAPI)    |
| soria-backend         | Service    | —        | —                   |
| soria-cockpit         | Deployment | 1        | Harbor (nginx SPA)  |
| soria-cockpit         | Service    | —        | —                   |
| soria-migrate-seed    | Job        | —        | Harbor (FastAPI)    |
| soria-config          | ConfigMap  | —        | —                   |
| soria-prospecting     | Ingress    | —        | —                   |
