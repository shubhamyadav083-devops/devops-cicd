"""Tests for Docker Compose files (Requirements 11.2, 11.4)."""
import os
import pytest
import yaml

STAGING_FILE = "docker-compose.staging.yml"
PRODUCTION_FILE = "docker-compose.production.yml"


def load_compose(filename):
    with open(filename) as f:
        return yaml.safe_load(f)


def test_staging_compose_exists():
    assert os.path.isfile(STAGING_FILE), f"{STAGING_FILE} does not exist"


def test_production_compose_exists():
    assert os.path.isfile(PRODUCTION_FILE), f"{PRODUCTION_FILE} does not exist"


def test_staging_image_uses_local_registry():
    compose = load_compose(STAGING_FILE)
    image = compose["services"]["app"]["image"]
    assert image.startswith("localhost:5000/"), (
        f"Staging app image '{image}' does not start with 'localhost:5000/'"
    )


def test_production_image_uses_local_registry():
    compose = load_compose(PRODUCTION_FILE)
    image = compose["services"]["app"]["image"]
    assert image.startswith("localhost:5000/"), (
        f"Production app image '{image}' does not start with 'localhost:5000/'"
    )


def test_staging_port_mapping():
    compose = load_compose(STAGING_FILE)
    ports = compose["services"]["app"]["ports"]
    host_ports = [str(p).split(":")[0] for p in ports]
    assert "8080" in host_ports, f"Staging does not map host port 8080; ports: {ports}"


def test_production_port_mapping():
    compose = load_compose(PRODUCTION_FILE)
    ports = compose["services"]["app"]["ports"]
    host_ports = [str(p).split(":")[0] for p in ports]
    assert "8081" in host_ports, f"Production does not map host port 8081; ports: {ports}"
