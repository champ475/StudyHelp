"""No DB involved — /health must answer even if Postgres is down."""

from fastapi.testclient import TestClient

from studyhelp.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
