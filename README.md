# ACEest Fitness & Gym

[![CI](https://github.com/mudit1024/aceest-fitness/actions/workflows/main.yml/badge.svg)](https://github.com/mudit1024/aceest-fitness/actions/workflows/main.yml)

A Flask REST API for gym client management: training programmes, calorie
estimates, client records, BMI, memberships, weekly adherence, workouts and
body metrics. It ships with a Pytest suite (100% line coverage), a
multi-stage Docker image, a GitHub Actions pipeline and a Jenkins build.

The service is a port of the original Tkinter desktop prototypes, which are
kept in [`legacy/`](legacy/) for reference.

---

## Contents

- [Project layout](#project-layout)
- [API reference](#api-reference)
- [Local setup](#local-setup)
- [Running the tests](#running-the-tests)
- [Docker](#docker)
- [CI/CD overview](#cicd-overview)
  - [GitHub Actions](#github-actions)
  - [Jenkins](#jenkins)
- [Configuration](#configuration)
- [Branching and versioning](#branching-and-versioning)

---

## Project layout

```
.
├── app.py                    # Entry point (python app.py / gunicorn app:app)
├── aceest/                   # Application package
│   ├── __init__.py           # create_app() factory, /, /health, JSON errors
│   ├── logic.py              # Pure business rules (calories, BMI, membership…)
│   ├── validation.py         # Request validation helpers
│   ├── db.py                 # SQLite connection handling and schema
│   ├── programs.py           # /programs, /calories
│   ├── clients.py            # /clients CRUD, BMI, membership, generator
│   ├── tracking.py           # progress, workouts, metrics
│   └── auth.py               # /login
├── tests/                    # Pytest suite (one file per module)
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # + pytest, pytest-cov, flake8
├── Dockerfile                # Multi-stage: base → test / runtime
├── .github/workflows/main.yml
├── Jenkinsfile
├── jenkins/                  # Ready-to-run Jenkins (Dockerfile + compose)
└── legacy/                   # Original Tkinter versions 1.0 – 3.2.4
```

`logic.py` has no Flask or database code, so the business rules can be unit
tested directly. The HTTP layer is split into one blueprint per feature.

## API reference

All request and response bodies are JSON. Errors use the form
`{"error": "<HTTP name>", "message": "<details>"}`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service info and list of endpoints |
| GET | `/health` | Liveness check |
| POST | `/login` | `{username, password}` → role; `401` if invalid |
| GET | `/programs` | All programmes (FL, MG, BG) |
| GET | `/programs/<code>` | One programme (case-insensitive code) |
| POST | `/calories` | `{weight, program}` → estimated daily kcal |
| GET / POST | `/clients` | List clients / create a client |
| GET / PUT / PATCH / DELETE | `/clients/<name>` | Read, update or delete a client |
| GET | `/clients/<name>/bmi` | BMI, category and risk note |
| GET | `/clients/<name>/membership` | Active / Expired, days remaining |
| POST | `/clients/<name>/program/generate` | Assign a random programme and plan |
| GET / POST | `/clients/<name>/progress` | Weekly adherence log and average |
| GET / POST | `/clients/<name>/workouts` | Workouts with nested exercises |
| GET / POST | `/clients/<name>/metrics` | Weight, waist and body-fat entries |

Client fields: `name` (required), `age`, `height` (cm), `weight` (kg),
`program` (`FL`/`MG`/`BG`), `target_weight`, `target_adherence` (0–100),
`membership_end` (`YYYY-MM-DD`). `calories` is calculated as
weight × programme factor (FL 22, MG 35, BG 26) and updated automatically.

Example:

```bash
curl -X POST localhost:5000/clients -H "Content-Type: application/json" \
     -d '{"name": "Arjun", "age": 28, "height": 175, "weight": 80, "program": "MG"}'

curl -X POST localhost:5000/clients/Arjun/workouts -H "Content-Type: application/json" \
     -d '{"workout_type": "Strength", "duration_min": 60,
          "exercises": [{"name": "Back Squat", "sets": 5, "reps": 5, "weight": 100}]}'
```

## Local setup

Prerequisites: Python 3.11+ and Git. Docker is optional.

```bash
git clone https://github.com/mudit1024/aceest-fitness.git
cd aceest-fitness

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

pip install -r requirements-dev.txt
python app.py
```

The API runs at <http://127.0.0.1:5000>. Open `/` to see every endpoint.
Data is stored in `instance/aceest_fitness.db`; delete that file to start
fresh. Set `FLASK_DEBUG=1` to enable auto-reload.

## Running the tests

```bash
pytest                                        # run the whole suite
pytest -v tests/test_clients.py               # one module, verbose
pytest -k bmi                                 # tests matching a keyword
pytest --cov=aceest --cov-report=term-missing # with coverage report
flake8 .                                      # lint (config in .flake8)
```

Each test gets its own temporary SQLite database through the `app` fixture
in [`tests/conftest.py`](tests/conftest.py), so tests are isolated and can
run in any order.

| Test file | Covers |
|---|---|
| `test_logic.py` | Calorie, BMI, membership and adherence rules, including boundaries |
| `test_app.py` | Health and index endpoints, JSON 404/405 handling |
| `test_programs.py` | Programme catalogue and calorie endpoint, including validation |
| `test_clients.py` | Client CRUD, validation, duplicates, BMI, membership, persistence |
| `test_tracking.py` | Progress, workouts and exercises, metrics, cascade delete |
| `test_auth.py` | Login, password hashing, programme generator |

## Docker

The [`Dockerfile`](Dockerfile) is a multi-stage build:

| Stage | Purpose |
|---|---|
| `base` | `python:3.12-slim`, production dependencies, application code |
| `test` | `base` + pytest/flake8 + `tests/`; default command runs the suite |
| `runtime` (default) | `base`, run by gunicorn as a non-root user, with a `HEALTHCHECK` |

How the image is kept small and secure:

- Slim base image, `pip --no-cache-dir`, and no compilers or build tools.
- `requirements.txt` is copied before the code, so the dependency layer is
  rebuilt only when dependencies change.
- `.dockerignore` keeps `.git`, virtualenvs, local databases and `legacy/`
  out of the build context.
- The container runs as an unprivileged `app` user that can write only to
  `/app/data`.
- The production server is gunicorn; the Flask dev server is not used.

```bash
# Run the tests inside a container
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test

# Build and run the service
docker build -t aceest-fitness .
docker run -d --name aceest -p 5000:5000 -v aceest-data:/app/data aceest-fitness
curl localhost:5000/health
```

## CI/CD overview

```
                         git push / pull request
                                   │
             ┌─────────────────────┴──────────────────────┐
             ▼                                            ▼
   GitHub Actions (.github/workflows/main.yml)   Jenkins (Jenkinsfile)
   ┌───────────────────────────┐                 ┌──────────────────────────┐
   │ 1. Build & Lint           │                 │ Checkout from GitHub     │
   │    flake8, compileall     │                 │ Clean venv build         │
   │ 2. Docker Image Assembly  │                 │ Lint                     │
   │    test + runtime images  │                 │ Pytest + JUnit/coverage  │
   │ 3. Automated Testing      │                 │ Docker build & test      │
   │    pytest in container,   │                 └──────────────────────────┘
   │    runtime smoke test     │                   secondary quality gate
   └───────────────────────────┘
```

Both pipelines use the same commands that engineers run locally (`flake8`,
`pytest`, `docker build`), so a green local run should also pass in CI.
Both fail the build if line coverage drops below 90%.

### GitHub Actions

The workflow in [`.github/workflows/main.yml`](.github/workflows/main.yml)
runs on every `push` and `pull_request`, and can also be started manually.
It has three jobs, chained with `needs:` so each runs only if the previous
one passed:

1. **Build & Lint.** Installs dependencies on Python 3.12, then runs a
   strict flake8 pass for syntax errors and undefined names, the full
   flake8 rule set, `compileall` and an import smoke test.
2. **Docker Image Assembly.** Builds the `test` and `runtime` images and
   passes them to the next job as a workflow artifact.
3. **Automated Testing.** Loads the images and runs the Pytest suite
   inside the `test` container, with a 90% coverage gate. It uploads a
   JUnit report, then starts the `runtime` container and checks
   `/health`, `/programs` and that the process is not running as root.

### Jenkins

Jenkins is the secondary BUILD and quality gate. The declarative
[`Jenkinsfile`](Jenkinsfile) runs these stages:

| Stage | What it does |
|---|---|
| Checkout | Pulls the latest commit from GitHub |
| Clean Build Environment | Deletes and recreates a Python venv, then installs `requirements-dev.txt` |
| Lint | flake8 and `compileall` |
| Unit Tests | Pytest with JUnit and coverage XML, published to Jenkins test results |
| Docker Build & Test | Builds the images and runs the suite in the container. Skipped automatically if the agent has no Docker access. |

The job polls GitHub every 5 minutes (`pollSCM('H/5 * * * *')`). A GitHub
webhook can trigger it immediately instead.

**Setting up Jenkins locally**

1. Start the bundled Jenkins image, which includes Python 3, the Docker CLI
   and the required plugins:
   ```bash
   docker compose -f jenkins/docker-compose.yml up -d --build
   ```
2. Open <http://localhost:8080>. Unlock Jenkins with the password printed by
   `docker exec aceest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword`,
   choose **Install suggested plugins** and create an admin user.
3. Create the job: **New Item → `aceest-fitness` → Pipeline**.
   Under *Pipeline*, choose **Pipeline script from SCM**, set SCM to **Git**,
   enter this repository's URL, set the branch to `*/main` and the script
   path to `Jenkinsfile`.
4. Click **Build Now**. The first run also registers the `pollSCM` trigger,
   so later pushes are built automatically.
5. Optional, for builds on every push: add a webhook in GitHub at
   *Settings → Webhooks* pointing to `http://<public-jenkins-url>/github-webhook/`
   (use a tunnel such as ngrok for a local Jenkins), and tick
   **GitHub hook trigger for GITScm polling** in the job.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ACEEST_DB` | `instance/aceest_fitness.db` (`/app/data/...` in Docker) | SQLite file path |
| `ACEEST_ADMIN_PASSWORD` | `admin` | Password for the seeded `admin` user. **Change this outside development.** |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Bind address for `python app.py` |
| `FLASK_DEBUG` | unset | `1` enables the debugger and reloader (local only) |

Passwords are stored as salted scrypt hashes. The legacy app stored them
in plain text.

## Branching and versioning

- `main` is always releasable. All work happens on short-lived branches
  that are merged with `--no-ff`, so each feature appears as one unit in the
  history:
  `feature/*` for application work, `infra/*` for Docker and CI, `docs/*`
  for documentation, and `fix/*` for bug fixes.
- Commit messages follow
  [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`,
  `fix:`, `test:`, `ci:`, `build:`, `docs:`, `refactor:`, `chore:`).
- Releases are tagged to match the evolution of the legacy prototypes:

| Tag | Milestone |
|---|---|
| `v1.0.0` | Flask core, programme catalogue, calorie calculator |
| `v2.0.0` | SQLite client management, BMI, membership |
| `v3.0.0` | Progress, workout and metrics tracking, login, programme generator |
| `v3.1.0` | Docker image, GitHub Actions and Jenkins pipelines, documentation |
