from fastapi.testclient import TestClient

from learning_companion.main import app


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}
