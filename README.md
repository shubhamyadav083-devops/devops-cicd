# DevOps CI/CD Pipeline

A Flask microservice with a fully automated GitLab CI/CD pipeline covering build, test, and multi-environment deployment using Docker.

## Project Structure

```
├── app/
│   └── main.py               # Flask application
├── tests/
│   ├── test_app.py           # App unit tests
│   ├── test_dockerfile.py    # Dockerfile validation tests
│   ├── test_compose.py       # Docker Compose validation tests
│   ├── test_pipeline.py      # Pipeline config tests
│   └── test_properties.py    # Property-based tests (Hypothesis)
├── .gitlab-ci.yml            # CI/CD pipeline definition
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.staging.yml
├── docker-compose.production.yml
├── requirements.txt
└── requirements-dev.txt
```

## Application

A minimal Flask app exposing a single health check endpoint:

```
GET /health  →  {"status": "ok"}  200
```

Runs on port `8080` by default (configurable via `PORT` env var).

## Docker

Multi-stage build — builder installs dependencies into a venv, runtime copies only what's needed and runs as a non-root user.

```bash
# Build
docker build -t myapp .

# Run
docker run -p 8080:8080 myapp
```

## CI/CD Pipeline

The `.gitlab-ci.yml` defines three stages:

| Stage  | Job               | Trigger                        |
|--------|-------------------|--------------------------------|
| build  | build-image       | every push / MR                |
| test   | test-unit         | after build                    |
| deploy | deploy-staging    | `main` branch (automatic)      |
| deploy | deploy-production | `main` branch (manual trigger) |

### Flow

1. `build-image` — builds and pushes a Docker image tagged with the commit SHA to a local registry, exports image refs as dotenv artifacts.
2. `test-unit` — runs `pytest` inside the built image, publishes JUnit XML reports.
3. `deploy-staging` — runs `docker compose -f docker-compose.staging.yml up -d` (port `8080`).
4. `deploy-production` — manual gate, runs `docker compose -f docker-compose.production.yml up -d` (port `8081`).

## Local Development

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run the app
python -m flask --app app.main run --port 8080

# Run tests
pytest --junitxml=reports/junit.xml
```

## Requirements

- Python 3.12+
- Docker 24+
- GitLab Runner with Docker executor and a local registry at `localhost:5000`
