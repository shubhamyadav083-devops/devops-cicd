# Implementation Plan: CI/CD Pipeline Automation

## Overview

Implement a fully local GitLab CI/CD pipeline for a Python/Flask application. Tasks progress from the application source and Dockerfile, through pipeline configuration, to Docker Compose deployment stacks and the test suite.

## Tasks

- [x] 1. Create the Flask application and dependencies
  - Create `app/main.py` with the Flask app, `/health` endpoint returning `{"status": "ok"}`, and `PORT` env var support
  - Create `requirements.txt` with `flask` as the only runtime dependency
  - Create `requirements-dev.txt` (or extend `requirements.txt`) with `pytest`, `pytest-junit`, `hypothesis`, and `requests` for testing
  - _Requirements: 10.1, 10.4_

  - [ ]* 1.1 Write property test for server PORT binding (Property 4)
    - **Property 4: Server Listens on Configured PORT**
    - Use `@given(st.integers(min_value=1024, max_value=65535))` with `@settings(max_examples=100)`
    - Start the Flask test client with `PORT=N` and assert `GET /health` returns 200 and `{"status": "ok"}`
    - Tag: `# Feature: cicd-pipeline-automation, Property 4: server listens on PORT env var`
    - **Validates: Requirements 10.4**

- [x] 2. Create the multi-stage Dockerfile
  - Write a two-stage `Dockerfile`: `builder` stage installs deps into `/app/.venv`; `runtime` stage copies venv and `app/`, adds a non-root `appuser`, sets `ENV PORT=8080`, and runs Flask via `CMD`
  - _Requirements: 10.2, 10.3, 10.4_

- [x] 3. Create Docker Compose environment files
  - Create `docker-compose.staging.yml` — maps host port `8080` to container `8080`, uses `localhost:5000/${IMAGE_NAME}:${IMAGE_TAG}`
  - Create `docker-compose.production.yml` — maps host port `8081` to container `8080`, uses same image reference
  - _Requirements: 4.1, 5.3, 11.3, 11.4_

- [x] 4. Create the `.gitlab-ci.yml` pipeline definition
  - [x] 4.1 Define global structure: `stages: [build, test, deploy]`, `default:` image/retry/interruptible, top-level `variables:` with `IMAGE_NAME`, `PORT`, `LOCAL_REGISTRY=localhost:5000`
    - _Requirements: 1.1, 9.1, 9.2_

  - [x] 4.2 Implement `build-image` job
    - Script: `docker build -f Dockerfile`, tag with `sha-$CI_COMMIT_SHORT_SHA` and `$CI_COMMIT_REF_SLUG`, push both tags to `localhost:5000`
    - Declare `artifacts: reports: dotenv:` writing `IMAGE_TAG`, `IMAGE_NAME`, `FULL_IMAGE_REF` to `build.env`
    - Add pip/venv cache with key including `requirements.txt` hash, `pull-push` policy on default branch
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 7.1, 8.1_

  - [x] 4.3 Implement `test-unit` job
    - Set `image: $FULL_IMAGE_REF` (from dotenv artifact) so tests run inside the built container
    - Script: `pytest --junitxml=reports/junit.xml`
    - Declare `artifacts: reports: junit: reports/junit.xml`, `expire_in: 30 days`, `when: always`
    - Add guard check: exit 1 with descriptive error if `FULL_IMAGE_REF` is unset
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 8.2, 9.3_

  - [x] 4.4 Implement `deploy-staging` job
    - Add `rules:` restricting to `$CI_COMMIT_BRANCH == "main"` and excluding `merge_request_event`
    - Script: guard check for `IMAGE_TAG`/`FULL_IMAGE_REF`, `echo "[deploy] environment=staging image=$FULL_IMAGE_REF"`, then `docker compose -f docker-compose.staging.yml up -d`
    - Declare `environment: name: staging, action: start`
    - _Requirements: 4.1, 4.2, 4.3, 6.2, 8.4_

  - [x] 4.5 Implement `deploy-production` job
    - Set `when: manual` and `rules:` restricting to `$CI_COMMIT_BRANCH == "main"`, excluding `merge_request_event`
    - Script: guard check for `IMAGE_TAG`/`FULL_IMAGE_REF`, `echo "[deploy] environment=production image=$FULL_IMAGE_REF"`, then `docker compose -f docker-compose.production.yml up -d`
    - Declare `environment: name: production, action: start`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.2, 8.4_

  - [x] 4.6 Add `workflow: rules:` for MR and branch pipelines
    - Allow pipelines on MR events (`$CI_PIPELINE_SOURCE == "merge_request_event"`) and branch pushes
    - Ensure deploy jobs are excluded from MR pipelines via their own `rules:`
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 5. Checkpoint — verify pipeline YAML structure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Write unit tests for pipeline configuration and application
  - [x] 6.1 Create `tests/test_app.py` — Flask test client tests
    - `test_health_returns_200`: assert `GET /health` → 200 and `{"status": "ok"}`
    - _Requirements: 10.1_

  - [x] 6.2 Create `tests/test_pipeline.py` — parse `.gitlab-ci.yml` with PyYAML and assert structural rules
    - Stage order equals `[build, test, deploy]`
    - Build job script contains `docker build -f Dockerfile`, pushes SHA and branch tags to `localhost:5000`
    - Build job declares `artifacts: reports: dotenv:` with `IMAGE_TAG` and `FULL_IMAGE_REF`
    - Test job `image:` references `$FULL_IMAGE_REF`; artifact `expire_in` ≥ 30 days; `when: always`
    - `deploy-staging` rules restrict to `main` branch; declares `environment: name: staging`; script contains `docker compose -f docker-compose.staging.yml up -d`
    - `deploy-production` has `when: manual`; declares `environment: name: production`; script contains `docker compose -f docker-compose.production.yml up -d`
    - Cache key includes `requirements.txt` hash
    - Deploy job scripts contain `echo` with `$IMAGE_TAG` and environment name
    - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 4.1, 4.3, 5.1, 5.3, 5.4, 7.1, 8.1, 8.2, 8.4_

  - [x] 6.3 Create `tests/test_dockerfile.py` — parse `Dockerfile` and assert structural rules
    - Contains ≥ 2 `FROM` instructions (multi-stage)
    - Final stage contains `USER` instruction with a non-root user
    - _Requirements: 10.2, 10.3_

  - [x] 6.4 Create `tests/test_compose.py` — assert Compose files exist and reference `localhost:5000`
    - Both `docker-compose.staging.yml` and `docker-compose.production.yml` are present
    - Each file's `image:` value starts with `localhost:5000/`
    - Staging maps port `8080`; production maps port `8081`
    - _Requirements: 11.2, 11.4_

- [x] 7. Write property-based tests
  - [ ]* 7.1 Write property test for no hardcoded secrets (Property 1)
    - **Property 1: No Hardcoded Secrets or Environment-Specific Values**
    - Use `@given(st.text(min_size=8))` with `@settings(max_examples=100)`
    - Assert that any generated credential-like string does not appear as a literal in `.gitlab-ci.yml` unless it starts with `$`; also statically scan YAML string literals against a credential pattern list (allow `localhost:5000`)
    - Tag: `# Feature: cicd-pipeline-automation, Property 1: no hardcoded secrets or environment-specific values`
    - **Validates: Requirements 4.2, 9.1, 9.2**

  - [ ]* 7.2 Write property test for required variable guard checks (Property 2)
    - **Property 2: Required Variable Guard Checks**
    - For each deploy/test job that requires a variable, generate environment states with that variable absent and assert the guard script exits before the first use of the variable
    - Tag: `# Feature: cicd-pipeline-automation, Property 2: required variable guard checks in job scripts`
    - **Validates: Requirements 9.3**

  - [ ]* 7.3 Write property test for JUnit XML well-formedness (Property 3)
    - **Property 3: JUnit XML Well-Formedness**
    - Use `@given(st.lists(test_case_strategy, min_size=1))` with `@settings(max_examples=100)`
    - Generate synthetic test-case dicts, produce JUnit XML via a helper, parse with `xml.etree.ElementTree`, assert root tag is `testsuites`/`testsuite`, ≥1 `<testsuite>`, and `<testcase>` count matches input
    - Tag: `# Feature: cicd-pipeline-automation, Property 3: JUnit XML is valid and well-formed`
    - **Validates: Requirements 3.2**

- [x] 8. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `max_examples=100`
- The local registry (`localhost:5000`) must be running before executing pipeline jobs locally
- Run tests with: `pytest --junitxml=reports/junit.xml`
