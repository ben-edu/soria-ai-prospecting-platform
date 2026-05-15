#!/usr/bin/env bash
# scripts/kc-setup-soria.sh
#
# Phase 13A-1 — Idempotent Keycloak setup for SORIA using official kcadm.sh.
#
# Creates:
#   - realm: soria
#   - confidential OIDC client: soria-cockpit
#   - realm roles: soria-user, soria-admin
#
# Required environment variables:
#   KC_ADMIN_USER
#   KC_ADMIN_PASS_B64
#
# No passwords or client secrets are stored in Git.

set -euo pipefail

: "${KC_ADMIN_USER:?Missing required env var KC_ADMIN_USER}"
: "${KC_ADMIN_PASS_B64:?Missing required env var KC_ADMIN_PASS_B64}"

KC_NAMESPACE="keycloak"
KC_POD="keycloak-0"
KC_INTERNAL_URL="http://localhost:8080"
KC_ADMIN_REALM="master"
KC_CONFIG="/tmp/kcadm-soria.config"
KCADM="/opt/bitnami/keycloak/bin/kcadm.sh"

REALM_NAME="soria"
CLIENT_ID="soria-cockpit"
APP_BASE_URL="https://react-admin.behnam.fr"
CALLBACK_URL="https://react-admin.behnam.fr/oauth2/callback"

KC_ADMIN_PASS=""

cleanup() {
  unset KC_ADMIN_PASS
  kubectl -n "${KC_NAMESPACE}" exec "${KC_POD}" -- rm -f "${KC_CONFIG}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

kcctl() {
  kubectl -n "${KC_NAMESPACE}" exec "${KC_POD}" -- "$@"
}

kcadm() {
  kcctl "${KCADM}" "$@"
}

echo ">>> Target Keycloak pod: ${KC_NAMESPACE}/${KC_POD}"
echo ">>> Target realm: ${REALM_NAME}"
echo ">>> Target client: ${CLIENT_ID}"

KC_ADMIN_PASS="$(printf '%s' "${KC_ADMIN_PASS_B64}" | base64 -d)"

echo ">>> Authenticating with Keycloak Admin CLI"

kubectl -n "${KC_NAMESPACE}" exec "${KC_POD}" -- env \
  KC_CLI_PASSWORD="${KC_ADMIN_PASS}" \
  "${KCADM}" config credentials \
    --server "${KC_INTERNAL_URL}" \
    --realm "${KC_ADMIN_REALM}" \
    --user "${KC_ADMIN_USER}" \
    --config "${KC_CONFIG}"

echo "    OK — authenticated."

echo ">>> Ensuring realm '${REALM_NAME}' exists and is enabled"

set +e
kcadm get "realms/${REALM_NAME}" --config "${KC_CONFIG}" >/dev/null 2>&1
REALM_EXISTS=$?
set -e

if [ "${REALM_EXISTS}" -ne 0 ]; then
  echo "    Realm '${REALM_NAME}' not found — creating."
  kcadm create realms \
    -s realm="${REALM_NAME}" \
    -s enabled=true \
    --config "${KC_CONFIG}"
  echo "    OK — realm created."
else
  echo "    Realm '${REALM_NAME}' already exists — enforcing enabled=true."
  kcadm update "realms/${REALM_NAME}" \
    -s enabled=true \
    --config "${KC_CONFIG}"
  echo "    OK — realm enabled."
fi

echo ">>> Ensuring OIDC confidential client '${CLIENT_ID}' exists"

CLIENT_JSON="$(kcadm get clients \
  -r "${REALM_NAME}" \
  -q "clientId=${CLIENT_ID}" \
  --config "${KC_CONFIG}")"

CLIENT_UUID="$(printf '%s\n' "${CLIENT_JSON}" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

if [ -z "${CLIENT_UUID}" ]; then
  echo "    Client '${CLIENT_ID}' not found — creating."

  kcadm create clients -r "${REALM_NAME}" \
    -s clientId="${CLIENT_ID}" \
    -s name='"SORIA Cockpit"' \
    -s enabled=true \
    -s protocol=openid-connect \
    -s publicClient=false \
    -s clientAuthenticatorType=client-secret \
    -s standardFlowEnabled=true \
    -s implicitFlowEnabled=false \
    -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=false \
    -s 'redirectUris=["https://react-admin.behnam.fr/oauth2/callback"]' \
    -s 'webOrigins=["https://react-admin.behnam.fr"]' \
    -s 'rootUrl="https://react-admin.behnam.fr"' \
    -s 'baseUrl="https://react-admin.behnam.fr"' \
    --config "${KC_CONFIG}"

  CLIENT_JSON="$(kcadm get clients \
    -r "${REALM_NAME}" \
    -q "clientId=${CLIENT_ID}" \
    --config "${KC_CONFIG}")"

  CLIENT_UUID="$(printf '%s\n' "${CLIENT_JSON}" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

  echo "    OK — client created."
else
  echo "    Client '${CLIENT_ID}' already exists."
fi

if [ -z "${CLIENT_UUID}" ]; then
  echo "FATAL: could not find or create client UUID for '${CLIENT_ID}'." >&2
  exit 1
fi

echo "    Client UUID: ${CLIENT_UUID}"

echo "    Applying desired client configuration."

kcadm update "clients/${CLIENT_UUID}" -r "${REALM_NAME}" \
  -s clientId="${CLIENT_ID}" \
  -s name='"SORIA Cockpit"' \
  -s enabled=true \
  -s protocol=openid-connect \
  -s publicClient=false \
  -s clientAuthenticatorType=client-secret \
  -s standardFlowEnabled=true \
  -s implicitFlowEnabled=false \
  -s directAccessGrantsEnabled=false \
  -s serviceAccountsEnabled=false \
  -s 'redirectUris=["https://react-admin.behnam.fr/oauth2/callback"]' \
  -s 'webOrigins=["https://react-admin.behnam.fr"]' \
  -s 'rootUrl="https://react-admin.behnam.fr"' \
  -s 'baseUrl="https://react-admin.behnam.fr"' \
  --config "${KC_CONFIG}"

echo "    OK — client configuration applied."

ensure_realm_role() {
  local role_name="$1"
  local role_description="$2"

  echo ">>> Ensuring realm role '${role_name}' exists"

  set +e
  kcadm get "roles/${role_name}" \
    -r "${REALM_NAME}" \
    --config "${KC_CONFIG}" >/dev/null 2>&1
  local role_exists=$?
  set -e

  if [ "${role_exists}" -ne 0 ]; then
    echo "    Role '${role_name}' not found — creating."

    kcadm create roles -r "${REALM_NAME}" \
      -s name="${role_name}" \
      -s description="${role_description}" \
      --config "${KC_CONFIG}"

    echo "    OK — role '${role_name}' created."
  else
    echo "    OK — role '${role_name}' already exists."
  fi
}

ensure_realm_role "soria-user" "Standard SORIA user role"
ensure_realm_role "soria-admin" "SORIA administrator role"

echo ">>> Retrieving client secret for '${CLIENT_ID}'"

CLIENT_SECRET_JSON="$(kcadm get \
  "clients/${CLIENT_UUID}/client-secret" \
  -r "${REALM_NAME}" \
  --config "${KC_CONFIG}")"

CLIENT_SECRET="$(printf '%s\n' "${CLIENT_SECRET_JSON}" | sed -n 's/.*"value"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

if [ -z "${CLIENT_SECRET}" ]; then
  echo "FATAL: client secret is empty." >&2
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Keycloak setup complete for SORIA"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Realm: ${REALM_NAME}"
echo "  Client ID: ${CLIENT_ID}"
echo "  Client UUID: ${CLIENT_UUID}"
echo ""
echo "  SORIA_OAUTH2_PROXY_CLIENT_SECRET=${CLIENT_SECRET}"
echo ""
echo "  Do NOT paste the client secret into chat."
echo ""
echo "  Future Kubernetes Secret command template:"
echo ""
echo "  COOKIE_SECRET=\"\$(openssl rand -base64 32 | tr -d '\\n')\""
echo "  kubectl -n soria-prospecting create secret generic soria-oauth-proxy \\"
echo "    --from-literal=client-id=${CLIENT_ID} \\"
echo "    --from-literal=client-secret='<PASTE_SORIA_OAUTH2_PROXY_CLIENT_SECRET_HERE>' \\"
echo "    --from-literal=cookie-secret=\"\${COOKIE_SECRET}\""
echo ""
echo "═══════════════════════════════════════════════════════════════"
