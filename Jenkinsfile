// Pipeline CI/CD: Checkout → Test (+cobertura) → Build → Scan (Trivy) → Push a Docker Hub → Deploy a Kubernetes
pipeline {
    agent any

    options {
        timeout(time: 20, unit: 'MINUTES')               // evita builds colgados que bloquean el executor
        disableConcurrentBuilds()                         // un build a la vez: no se pisan las etiquetas :latest
        buildDiscarder(logRotator(numToKeepStr: '10'))    // conserva solo los últimos 10 builds (disco)
        timestamps()                                      // hora en cada línea del log
    }

    environment {
        IMAGE_NAME    = "jasonmsaravia/devops-taskapi"
        // Caché de pip fuera del workspace: sobrevive a cleanWs() y acelera el stage Test
        PIP_CACHE_DIR = "${JENKINS_HOME}/.cache/pip"
        TRIVY_IMAGE   = "aquasec/trivy:0.57.1"
    }

    triggers {
        pollSCM('H/5 * * * *')   // SCM polling cada ~5 min (H reparte la carga)
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet -r requirements-dev.txt
                    pytest tests/ -v \
                        --junit-xml=test-report.xml \
                        --cov=app --cov-report=term --cov-report=html:coverage-html \
                        --cov-fail-under=80
                '''
            }
            post {
                always {
                    junit 'test-report.xml'                                        // reporte de tests en la UI
                    archiveArtifacts artifacts: 'coverage-html/**', allowEmptyArchive: true  // reporte de cobertura
                }
            }
        }

        stage('Build') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
                sh "docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest"
            }
        }

        stage('Scan') {
            steps {
                // Bloquea la publicación si la imagen tiene vulnerabilidades CRITICAL con arreglo disponible
                sh """
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v trivy-cache:/root/.cache \
                        ${TRIVY_IMAGE} image --quiet --scanners vuln --ignore-unfixed \
                        --severity CRITICAL --exit-code 1 ${IMAGE_NAME}:${BUILD_NUMBER}
                """
            }
        }

        stage('Push') {
            steps {
                // La credencial se inyecta solo dentro de este bloque y Jenkins la enmascara en el log
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest
                    '''
                }
            }
        }

        stage('Deploy') {
            environment {
                KUBECONFIG = '/tmp/kubeconfig'   // copia parcheada, solo para este stage
            }
            steps {
                sh '''
                    # 1. Copiar el kubeconfig de Docker Desktop y adaptarlo al contenedor:
                    #    127.0.0.1 / kubernetes.docker.internal apuntan al propio contenedor,
                    #    host.docker.internal apunta al equipo anfitrión donde corre Kubernetes
                    cp "$HOME/.kube/config" "$KUBECONFIG"
                    sed -i -E 's#https://(127\\.0\\.0\\.1|localhost|kubernetes\\.docker\\.internal)#https://host.docker.internal#g' "$KUBECONFIG"
                    sed -i 's/certificate-authority-data:.*/insecure-skip-tls-verify: true/' "$KUBECONFIG"

                    # 2. Aplicar manifiestos (primero el namespace: kubectl recorre la carpeta en orden alfabético)
                    kubectl apply -f k8s/namespace.yaml
                    kubectl apply -f k8s/

                    # 3. Fijar la imagen exacta de este build (trazabilidad: pod ↔ build de Jenkins)
                    kubectl set image deployment/taskapi taskapi="$IMAGE_NAME:$BUILD_NUMBER" -n devops-project

                    # 4. Esperar el rolling update (máx. 2 min); si no termina, el stage falla
                    kubectl rollout status deployment/taskapi -n devops-project --timeout=120s
                    kubectl get pods -n devops-project -o wide
                '''
            }
            post {
                failure {
                    // Si el despliegue no quedó sano, volver a la versión anterior que sí funcionaba
                    sh 'kubectl rollout undo deployment/taskapi -n devops-project || true'
                }
            }
        }
    }

    post {
        always {
            sh 'docker logout || true'
            // Borra la imagen local del build para no llenar el disco del servidor CI
            sh "docker rmi ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest || true"
            cleanWs()
        }
        success {
            echo "Pipeline OK — imagen ${IMAGE_NAME}:${BUILD_NUMBER} publicada y desplegada en Kubernetes"
        }
        failure {
            echo "Pipeline FAILED en build #${BUILD_NUMBER} — revisar logs"
        }
    }
}
