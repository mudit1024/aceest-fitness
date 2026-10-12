# Jenkins controller with the tools the ACEest pipeline needs:
# Python 3 (venv + pip) and the Docker CLI (talks to the host's daemon).
FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

USER jenkins

# Plugins used by the Jenkinsfile, pre-installed so setup is quick.
RUN jenkins-plugin-cli --plugins \
    git \
    github \
    workflow-aggregator \
    pipeline-stage-view \
    junit \
    timestamper \
    credentials-binding
