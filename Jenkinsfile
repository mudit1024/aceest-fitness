// Jenkins BUILD & quality gate for ACEest Fitness & Gym.
//
// Pulls the latest code from GitHub, builds a clean Python environment,
// lints, runs the Pytest suite, then builds and tests the Docker image
// (Docker stages run only when the agent can reach a Docker daemon).

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    // Poll GitHub every ~5 minutes; a GitHub webhook can replace this.
    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        IMAGE = 'aceest-fitness'
        TAG   = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty="format:%h %an: %s"'
            }
        }

        stage('Clean Build Environment') {
            steps {
                sh '''
                    rm -rf .venv reports
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python --version
                    pip install --quiet --upgrade pip
                    pip install --quiet -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    . .venv/bin/activate
                    flake8 . --select=E9,F63,F7,F82 --show-source
                    flake8 . --statistics
                    python -m compileall -q app.py aceest
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    mkdir -p reports
                    pytest -v \
                        --junitxml=reports/junit.xml \
                        --cov=aceest --cov-report=term-missing \
                        --cov-report=xml:reports/coverage.xml \
                        --cov-fail-under=90
                '''
            }
            post {
                always {
                    junit 'reports/junit.xml'
                    archiveArtifacts artifacts: 'reports/*.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Docker Build & Test') {
            when {
                expression { sh(script: 'docker info > /dev/null 2>&1', returnStatus: true) == 0 }
            }
            steps {
                sh 'docker build --target test -t $IMAGE:test-$TAG .'
                sh 'docker run --rm $IMAGE:test-$TAG'
                sh 'docker build --target runtime -t $IMAGE:$TAG -t $IMAGE:latest .'
                sh 'docker images $IMAGE'
            }
            post {
                always {
                    sh 'docker image rm $IMAGE:test-$TAG > /dev/null 2>&1 || true'
                }
            }
        }
    }

    post {
        success {
            echo "BUILD #${env.BUILD_NUMBER} passed: ${env.IMAGE}:${env.TAG} is ready."
        }
        failure {
            echo "BUILD #${env.BUILD_NUMBER} failed - check the stage logs above."
        }
    }
}
