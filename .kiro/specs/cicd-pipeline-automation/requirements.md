# Requirements Document

## Introduction

A complete GitLab CI/CD pipeline project that automates build, test, and deployment workflows for a containerized application using Docker. The project demonstrates real-world DevOps skills including pipeline configuration, Docker image management, environment-based deployments, and pipeline observability — making it a strong resume artifact.

## Glossary

- **Pipeline**: The GitLab CI/CD pipeline defined in `.gitlab-ci.yml` that orchestrates all automated workflows
- **Runner**: The GitLab Runner agent that executes pipeline jobs
- **Job**: A single unit of work within a pipeline stage (e.g., build, test, deploy)
- **Stage**: A logical grouping of jobs that run in sequence (e.g., build → test → deploy)
- **Image**: A Docker container image built from a Dockerfile
- **Registry**: A local Docker registry container (`registry:2` on `localhost:5000`) where built images are stored and pulled from during the pipeline
- **Artifact**: A file or directory produced by a job and passed to subsequent jobs
- **Environment**: A named local Docker Compose stack (e.g., `staging`, `production`) that runs the application container on the developer's machine
- **Service**: A Docker container started alongside a job to provide dependencies (e.g., a test database)
- **Cache**: Reusable files persisted between pipeline runs to speed up jobs (e.g., dependency directories)
- **Merge_Request**: A GitLab merge request proposing changes from a source branch to a target branch
- **Application**: The sample containerized web application used as the subject of the pipeline
- **Local Registry**: A Docker registry container (`registry:2`) running on `localhost:5000` used to store and pull images locally

---

## Requirements

### Requirement 1: Pipeline Structure and Stage Ordering

**User Story:** As a DevOps engineer, I want a clearly defined multi-stage pipeline, so that build, test, and deployment steps execute in a predictable, sequential order.

#### Acceptance Criteria

1. THE Pipeline SHALL define stages in the following order: `build`, `test`, `deploy`
2. WHEN a job in the `build` stage fails, THE Pipeline SHALL not execute any jobs in the `test` or `deploy` stages
3. WHEN a job in the `test` stage fails, THE Pipeline SHALL not execute any jobs in the `deploy` stage
4. THE Pipeline SHALL execute all jobs within the same stage in parallel where no explicit dependency is declared

---

### Requirement 2: Docker Image Build

**User Story:** As a DevOps engineer, I want the pipeline to build a Docker image from the application source, so that the application is packaged consistently for every commit.

#### Acceptance Criteria

1. WHEN a pipeline is triggered, THE Pipeline SHALL build a Docker image using the `Dockerfile` at the repository root
2. THE Pipeline SHALL tag the built image with the Git commit SHA
3. THE Pipeline SHALL tag the built image with the branch name
4. WHEN the build succeeds, THE Pipeline SHALL push the tagged image to the GitLab Container Registry
5. IF the `Dockerfile` is missing or contains a syntax error, THEN THE Pipeline SHALL fail the build job and report the error in the job log

---

### Requirement 3: Automated Testing

**User Story:** As a DevOps engineer, I want the pipeline to run automated tests inside a container, so that code quality is verified against every change before deployment.

#### Acceptance Criteria

1. WHEN the `build` stage completes successfully, THE Pipeline SHALL execute unit tests inside a Docker container derived from the built image
2. THE Pipeline SHALL produce a JUnit-compatible XML test report as a job artifact
3. WHEN all tests pass, THE Pipeline SHALL mark the test job as succeeded
4. IF one or more tests fail, THEN THE Pipeline SHALL mark the test job as failed and surface the test report in the GitLab UI
5. WHERE a test database is required, THE Pipeline SHALL start the database as a Docker service alongside the test job

---

### Requirement 4: Staging Deployment

**User Story:** As a DevOps engineer, I want every successful merge to the default branch to deploy automatically to a local staging environment, so that changes are continuously validated in a production-like setting on the developer's machine.

#### Acceptance Criteria

1. WHEN a pipeline on the default branch (`main`) completes the `test` stage successfully, THE Pipeline SHALL deploy the built image to the local `staging` Docker Compose stack using `docker compose -f docker-compose.staging.yml up -d`
2. THE Pipeline SHALL pass environment-specific configuration to the staging deployment via CI/CD variables, not hardcoded values
3. WHEN the staging deployment succeeds, THE Pipeline SHALL mark the `staging` environment as the active deployment in GitLab Environments
4. IF the staging deployment fails, THEN THE Pipeline SHALL mark the deploy job as failed and retain the previous deployment as active

---

### Requirement 5: Production Deployment with Manual Gate

**User Story:** As a DevOps engineer, I want production deployments to require a manual approval step, so that releases to production are intentional and controlled.

#### Acceptance Criteria

1. WHEN the staging deployment succeeds, THE Pipeline SHALL create a manual deploy job for the production environment
2. THE Pipeline SHALL not deploy to production until an authorized user triggers the manual job
3. WHEN the manual production deploy job is triggered, THE Pipeline SHALL deploy the same image SHA that was deployed to staging to the local `production` Docker Compose stack using `docker compose -f docker-compose.production.yml up -d`
4. WHEN the production deployment succeeds, THE Pipeline SHALL mark the `production` environment as the active deployment in GitLab Environments
5. IF the production deployment fails, THEN THE Pipeline SHALL mark the deploy job as failed without rolling back automatically

---

### Requirement 6: Merge Request Pipelines

**User Story:** As a developer, I want pipelines to run on merge requests so that I get fast feedback on my changes before they are merged.

#### Acceptance Criteria

1. WHEN a Merge_Request is opened or updated, THE Pipeline SHALL run the `build` and `test` stages
2. WHILE a pipeline is running on a Merge_Request, THE Pipeline SHALL not execute any `deploy` stage jobs
3. THE Pipeline SHALL report the pipeline status back to the Merge_Request so the result is visible before merging

---

### Requirement 7: Dependency Caching

**User Story:** As a DevOps engineer, I want pipeline dependencies to be cached between runs, so that pipeline execution time is reduced for unchanged dependencies.

#### Acceptance Criteria

1. THE Pipeline SHALL cache the application dependency directory (e.g., `node_modules` or equivalent) keyed by the dependency lock file hash
2. WHEN a cached dependency set is available and the lock file is unchanged, THE Pipeline SHALL restore the cache before installing dependencies
3. WHEN the lock file changes, THE Pipeline SHALL invalidate the existing cache and rebuild it after installing the updated dependencies

---

### Requirement 8: Pipeline Artifacts and Observability

**User Story:** As a DevOps engineer, I want pipeline jobs to produce and retain artifacts, so that build outputs and test results are accessible for debugging and auditing.

#### Acceptance Criteria

1. THE Pipeline SHALL retain the Docker image digest and tag as a dotenv artifact passed from the build job to downstream jobs
2. THE Pipeline SHALL retain test reports for a minimum of 30 days
3. THE Pipeline SHALL retain build logs for every job
4. WHEN a deploy job completes, THE Pipeline SHALL output the deployed image tag and target environment name to the job log

---

### Requirement 9: Secret and Credential Management

**User Story:** As a DevOps engineer, I want all secrets and credentials to be stored as protected CI/CD variables, so that sensitive values are never exposed in the repository or job logs.

#### Acceptance Criteria

1. THE Pipeline SHALL read registry credentials and environment configuration exclusively from GitLab CI/CD variables
2. THE Pipeline SHALL not contain any hardcoded credentials, tokens, or environment-specific values in `.gitlab-ci.yml` or any committed file
3. WHEN a required CI/CD variable is absent, THE Pipeline SHALL fail the affected job with a descriptive error message before attempting to use the missing value

---

### Requirement 10: Application and Dockerfile

**User Story:** As a DevOps engineer, I want a working sample application with a production-ready Dockerfile, so that the pipeline has a realistic subject to build, test, and deploy.

#### Acceptance Criteria

1. THE Application SHALL be a minimal HTTP server that responds with a health-check endpoint at `/health`
2. THE Dockerfile SHALL use a multi-stage build to produce a minimal runtime image
3. THE Dockerfile SHALL not run the application process as the root user
4. WHEN the container starts, THE Application SHALL be reachable on the port defined by the `PORT` environment variable, defaulting to `8080`

---

### Requirement 11: Local Pipeline Execution

**User Story:** As a developer, I want to run the entire CI/CD pipeline locally on my machine, so that I can validate pipeline behavior without pushing to a remote GitLab instance.

#### Acceptance Criteria

1. THE Pipeline SHALL be executable locally using `gitlab-runner exec` or a GitLab Runner running in Docker on the developer's machine
2. THE Pipeline SHALL use a local Docker registry container (`registry:2` on `localhost:5000`) as the image store when running locally, instead of the GitLab Container Registry
3. WHEN running locally, THE Pipeline SHALL bring up the `staging` or `production` Docker Compose stack on the local Docker network
4. THE project SHALL include `docker-compose.staging.yml` and `docker-compose.production.yml` files that define the local deployment stacks for each environment
