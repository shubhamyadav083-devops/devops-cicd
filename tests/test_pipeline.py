"""
Structural tests for .gitlab-ci.yml pipeline configuration.

Validates: Requirements 1.1, 2.1-2.4, 3.1, 3.2, 4.1, 4.3, 5.1, 5.3, 5.4, 7.1, 8.1, 8.2, 8.4
"""

import yaml
import pytest

with open(".gitlab-ci.yml") as f:
    ci = yaml.safe_load(f)

# Helpers
def build_script():
    return " ".join(ci["build-image"]["script"])

def staging_script():
    return " ".join(str(s) for s in ci["deploy-staging"]["script"])

def production_script():
    return " ".join(str(s) for s in ci["deploy-production"]["script"])


# --- Stage order ---

def test_stage_order():
    assert ci["stages"] == ["build", "test", "deploy"]


# --- Build job ---

def test_build_job_script_contains_docker_build():
    assert "docker build -f Dockerfile" in build_script()

def test_build_job_pushes_sha_tag():
    assert "sha-$CI_COMMIT_SHORT_SHA" in build_script()

def test_build_job_pushes_branch_tag():
    assert "$CI_COMMIT_REF_SLUG" in build_script()

def test_build_job_pushes_to_local_registry():
    # The script uses $LOCAL_REGISTRY which is defined as localhost:5000 in variables
    script = build_script()
    variables = ci.get("variables", {})
    local_registry = variables.get("LOCAL_REGISTRY", "")
    assert "localhost:5000" in local_registry or "localhost:5000" in script

def test_build_job_dotenv_artifact():
    assert ci["build-image"]["artifacts"]["reports"]["dotenv"] == "build.env"

def test_build_job_dotenv_contains_image_tag():
    assert "IMAGE_TAG=" in build_script()

def test_build_job_dotenv_contains_full_image_ref():
    assert "FULL_IMAGE_REF=" in build_script()


# --- Test job ---

def test_test_job_uses_full_image_ref():
    assert ci["test-unit"]["image"] == "$FULL_IMAGE_REF"

def test_test_job_artifact_expire_in():
    assert ci["test-unit"]["artifacts"]["expire_in"] == "30 days"

def test_test_job_artifact_when_always():
    assert ci["test-unit"]["artifacts"]["when"] == "always"


# --- Deploy staging ---

def test_deploy_staging_rules_restrict_to_main():
    rules = ci["deploy-staging"]["rules"]
    conditions = [r.get("if", "") for r in rules]
    assert any("main" in c for c in conditions)

def test_deploy_staging_environment_name():
    assert ci["deploy-staging"]["environment"]["name"] == "staging"

def test_deploy_staging_script_contains_compose():
    assert "docker compose -f docker-compose.staging.yml up -d" in staging_script()

def test_deploy_staging_log_output():
    assert "echo" in staging_script() and "$IMAGE_TAG" in staging_script()


# --- Deploy production ---

def test_deploy_production_when_manual():
    assert ci["deploy-production"]["when"] == "manual"

def test_deploy_production_environment_name():
    assert ci["deploy-production"]["environment"]["name"] == "production"

def test_deploy_production_script_contains_compose():
    assert "docker compose -f docker-compose.production.yml up -d" in production_script()

def test_deploy_production_log_output():
    assert "echo" in production_script() and "$IMAGE_TAG" in production_script()


# --- Cache ---

def test_cache_key_includes_requirements():
    cache_key = ci["build-image"]["cache"]["key"]
    assert "requirements" in cache_key
