pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        REGISTRY          = 'harbor.proxbenovh.cloud'
        PROJECT           = 'devops-project-harbor'
        BACKEND_IMAGE     = "${REGISTRY}/${PROJECT}/soria-backend"
        COCKPIT_IMAGE     = "${REGISTRY}/${PROJECT}/soria-cockpit"
        KUBECONFIG        = '/var/lib/jenkins/.kube/config-afpa-k3s'
        K8S_NAMESPACE     = 'soria-prospecting'
        KUSTOMIZE_OVERLAY = 'kubernetes/soria-prospecting/overlays/prod'
        PUBLIC_HOST       = 'https://react-admin.behnam.fr'
        VITE_API_BASE_URL = 'https://react-admin.behnam.fr/api/v1'
    }

    stages {
        stage('Checkout info') {
            steps {
                sh '''
                    echo "=== current directory ==="
                    pwd

                    echo "=== branch name ==="
                    echo "${BRANCH_NAME}"

                    echo "=== git commit ==="
                    git rev-parse --short HEAD

                    echo "=== git commit message ==="
                    git log -1 --pretty=%B
                '''
            }
        }

        stage('Resolve SHA') {
            steps {
                script {
                    env.GIT_SHA = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }

                echo "Using image tag: ${env.GIT_SHA}"
            }
        }

        stage('Frontend quality gates') {
            steps {
                sh '''
                    docker run --rm \
                      --user "$(id -u):$(id -g)" \
                      -e HOME=/tmp \
                      -e VITE_API_BASE_URL="${VITE_API_BASE_URL}" \
                      -v "$PWD/frontend/cockpit:/work" \
                      -w /work \
                      node:22-alpine \
                      sh -lc "npm ci && npm run type-check && npm run build"
                '''
            }
        }

        stage('Backend quality gates') {
            steps {
                sh '''
                    docker run --rm \
                      --user "$(id -u):$(id -g)" \
                      -e HOME=/tmp \
                      -e UV_LINK_MODE=copy \
                      -v "$PWD/backend:/work" \
                      -w /work \
                      python:3.12-slim \
                      sh -lc '
                        python -m pip install --user --no-cache-dir uv
                        export PATH="$HOME/.local/bin:$PATH"
                        uv sync
                        uv run pytest
                        uv run ruff check .
                      '
                '''
            }
        }

        stage('Docker login to Harbor') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'harbor-robot-devops-project-harbor',
                    usernameVariable: 'HARBOR_USERNAME',
                    passwordVariable: 'HARBOR_PASSWORD'
                )]) {
                    sh '''
                        set +x
                        echo "${HARBOR_PASSWORD}" | docker login "${REGISTRY}" \
                          -u "${HARBOR_USERNAME}" \
                          --password-stdin
                        set -x
                    '''
                }
            }
        }

        stage('Build backend image') {
            steps {
                sh '''
                    docker build \
                      -t "${BACKEND_IMAGE}:${GIT_SHA}" \
                      -f backend/Dockerfile \
                      backend
                '''
            }
        }

        stage('Push backend image') {
            steps {
                sh '''
                    docker push "${BACKEND_IMAGE}:${GIT_SHA}"
                '''
            }
        }

        stage('Build cockpit image') {
            steps {
                sh '''
                    docker build \
                      --build-arg VITE_API_BASE_URL="${VITE_API_BASE_URL}" \
                      -t "${COCKPIT_IMAGE}:${GIT_SHA}" \
                      -f frontend/cockpit/Dockerfile \
                      frontend/cockpit
                '''
            }
        }

        stage('Push cockpit image') {
            steps {
                sh '''
                    docker push "${COCKPIT_IMAGE}:${GIT_SHA}"
                '''
            }
        }

        stage('Render Kubernetes manifests') {
            steps {
                sh '''
                    kubectl kustomize "${KUSTOMIZE_OVERLAY}" > "/tmp/soria-rendered-${BUILD_NUMBER}.yaml"

                    echo "=== rendered important lines ==="
                    grep -E "soria-backend|soria-cockpit|soria-migrate-seed|react-admin.behnam.fr" "/tmp/soria-rendered-${BUILD_NUMBER}.yaml" | head -80 || true
                '''
            }
        }

        stage('Kubernetes preflight') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    echo "=== kubectl path ==="
                    which kubectl

                    echo "=== kubeconfig path ==="
                    echo "${KUBECONFIG}"
                    test -f "${KUBECONFIG}"

                    echo "=== namespace-scoped access check ==="
                    kubectl get pods -n "${K8S_NAMESPACE}" >/dev/null

                    echo "=== namespace resources ==="
                    kubectl get pods,svc,ingress -n "${K8S_NAMESPACE}" || true

                    echo "=== required secrets ==="
                    kubectl get secret soria-secrets -n "${K8S_NAMESPACE}"
                    kubectl get secret harbor-regcred -n "${K8S_NAMESPACE}"
                '''
            }
        }

        stage('Update Kustomize tags') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    python3 - <<'PY'
from pathlib import Path
import os
import re

overlay = Path(os.environ["KUSTOMIZE_OVERLAY"])
path = overlay / "kustomization.yaml"
sha = os.environ["GIT_SHA"]

text = path.read_text()
text = re.sub(r"newTag: .*", f"newTag: {sha}", text)
path.write_text(text)

print(path.read_text())
PY

                    kubectl kustomize "${KUSTOMIZE_OVERLAY}" > "/tmp/soria-rendered-${BUILD_NUMBER}.yaml"

                    echo "=== validate rendered images use SHA ==="
                    grep -q "${BACKEND_IMAGE}:${GIT_SHA}" "/tmp/soria-rendered-${BUILD_NUMBER}.yaml"
                    grep -q "${COCKPIT_IMAGE}:${GIT_SHA}" "/tmp/soria-rendered-${BUILD_NUMBER}.yaml"

                    echo "=== validate no latest image remains ==="
                    if grep -E 'image: .*:latest' "/tmp/soria-rendered-${BUILD_NUMBER}.yaml" >/dev/null; then
                      echo "ERROR: rendered manifest still contains :latest"
                      exit 1
                    fi
                '''
            }
        }

        stage('Apply manifests') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    kubectl delete job soria-migrate-seed -n "${K8S_NAMESPACE}" --ignore-not-found
                    kubectl apply -k "${KUSTOMIZE_OVERLAY}"
                '''
            }
        }

        stage('Wait for PostgreSQL') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    kubectl rollout status deployment/soria-postgres -n "${K8S_NAMESPACE}" --timeout=180s
                '''
            }
        }

        stage('Run migration/seed job') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    kubectl wait --for=condition=complete job/soria-migrate-seed -n "${K8S_NAMESPACE}" --timeout=300s
                    kubectl logs job/soria-migrate-seed -n "${K8S_NAMESPACE}"
                '''
            }
        }

        stage('Wait for rollout') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    kubectl rollout status deployment/soria-backend -n "${K8S_NAMESPACE}" --timeout=180s
                    kubectl rollout status deployment/soria-cockpit -n "${K8S_NAMESPACE}" --timeout=180s
                '''
            }
        }

        stage('Validate in-cluster') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    echo "=== Kubernetes resources ==="
                    kubectl get pods,svc,ingress -n "${K8S_NAMESPACE}"

                    echo "=== live backend image ==="
                    kubectl get deployment/soria-backend -n "${K8S_NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}'
                    echo

                    echo "=== live cockpit image ==="
                    kubectl get deployment/soria-cockpit -n "${K8S_NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}'
                    echo

                    echo "=== validate live backend image tag ==="
                    test "$(kubectl get deployment/soria-backend -n "${K8S_NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}')" = "${BACKEND_IMAGE}:${GIT_SHA}"

                    echo "=== validate live cockpit image tag ==="
                    test "$(kubectl get deployment/soria-cockpit -n "${K8S_NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}')" = "${COCKPIT_IMAGE}:${GIT_SHA}"
                '''
            }
        }

        stage('Post-deploy public validation') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    echo "=== public frontend validation ==="
                    curl -k -f -I --retry 5 --retry-delay 5 --retry-connrefused "${PUBLIC_HOST}/"

                    echo "=== public backend health validation ==="
                    curl -k -fsS --retry 5 --retry-delay 5 --retry-connrefused "${PUBLIC_HOST}/api/v1/health"
                '''
            }
        }

        stage('Deployment skipped on non-main') {
            when {
                not {
                    branch 'main'
                }
            }
            steps {
                echo "Branch is ${env.BRANCH_NAME}. Images were built and pushed, manifests rendered, but Kubernetes deployment was skipped because this is not main."
            }
        }
    }

    post {
        always {
            sh '''
                rm -f "/tmp/soria-rendered-${BUILD_NUMBER}.yaml" || true
            '''
        }

        failure {
            echo "Pipeline failed."
        }

        success {
            echo "Pipeline completed successfully."
        }
    }
}
