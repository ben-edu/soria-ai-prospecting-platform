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
                echo "Branch: ${env.BRANCH_NAME}"
                echo "Commit: ${env.GIT_COMMIT}"
            }
        }

        stage('Resolve SHA') {
            steps {
                script {
                    env.GIT_SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    echo "GIT_SHA=${env.GIT_SHA}"
                }
            }
        }

        stage('Frontend quality gates') {
            steps {
                dir('frontend/cockpit') {
                    sh 'npm ci'
                    sh 'npm run type-check'
                    sh 'npm run build'
                }
            }
        }

        stage('Backend quality gates') {
            steps {
                dir('backend') {
                    sh 'uv sync'
                    sh 'uv run pytest'
                    sh 'uv run ruff check .'
                }
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
                sh 'docker push "${BACKEND_IMAGE}:${GIT_SHA}"'
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
                sh 'docker push "${COCKPIT_IMAGE}:${GIT_SHA}"'
            }
        }

        stage('Render Kubernetes manifests') {
            steps {
                sh '''
                    kubectl kustomize "${KUSTOMIZE_OVERLAY}" > "/tmp/soria-rendered-${BUILD_NUMBER}.yaml"
                    grep -E "soria-backend|soria-cockpit|soria-migrate-seed|react-admin.behnam.fr" "/tmp/soria-rendered-${BUILD_NUMBER}.yaml" | head -80 || true
                '''
            }
        }

        stage('Kubernetes preflight') {
            when {
                branch 'main'
            }
            steps {
                sh 'kubectl get nodes'
                sh "kubectl get ns ${K8S_NAMESPACE}"

                script {
                    def secretsExist = sh(
                        returnStatus: true,
                        script: "kubectl get secret soria-secrets -n ${K8S_NAMESPACE} > /dev/null 2>&1"
                    )
                    if (secretsExist != 0) {
                        error "Required secret 'soria-secrets' not found in namespace ${K8S_NAMESPACE}. Create it before deploying."
                    }

                    def regcredExist = sh(
                        returnStatus: true,
                        script: "kubectl get secret harbor-regcred -n ${K8S_NAMESPACE} > /dev/null 2>&1"
                    )
                    if (regcredExist != 0) {
                        error "Required secret 'harbor-regcred' not found in namespace ${K8S_NAMESPACE}. Copy it from fastapi-platform before deploying."
                    }
                }
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
                sh 'kubectl rollout status deployment/soria-postgres -n "${K8S_NAMESPACE}" --timeout=180s'
            }
        }

        stage('Run migration/seed job') {
            when {
                branch 'main'
            }
            steps {
                sh 'kubectl wait --for=condition=complete job/soria-migrate-seed -n "${K8S_NAMESPACE}" --timeout=300s'
                sh 'kubectl logs job/soria-migrate-seed -n "${K8S_NAMESPACE}"'
            }
        }

        stage('Wait for rollout') {
            when {
                branch 'main'
            }
            steps {
                sh 'kubectl rollout status deployment/soria-backend -n "${K8S_NAMESPACE}" --timeout=180s'
                sh 'kubectl rollout status deployment/soria-cockpit -n "${K8S_NAMESPACE}" --timeout=180s'
            }
        }

        stage('Validate in-cluster') {
            when {
                branch 'main'
            }
            steps {
                sh 'kubectl get pods,svc,ingress -n "${K8S_NAMESPACE}"'
            }
        }

        stage('Post-deploy public validation') {
            when {
                branch 'main'
            }
            steps {
                sh 'curl -k -f -I "${PUBLIC_HOST}/"'
                sh 'curl -k -fsS "${PUBLIC_HOST}/api/v1/health"'
            }
        }

        stage('Deployment skipped on non-main') {
            when {
                not {
                    branch 'main'
                }
            }
            steps {
                echo "Branch is ${env.BRANCH_NAME}. Images were built and pushed, but Kubernetes deployment was skipped because this is not main."
            }
        }
    }

    post {
        always {
            sh 'docker logout "${REGISTRY}" || true'
            sh 'rm -f "/tmp/soria-rendered-${BUILD_NUMBER}.yaml" || true'
        }
        failure {
            echo "Pipeline failed. Check the logs above for details."
        }
        success {
            echo "Pipeline completed successfully."
        }
    }
}
