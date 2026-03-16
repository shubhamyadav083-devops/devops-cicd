import pytest
from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_returns_200(client):
    """Validates: Requirements 10.1"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
