from fastapi.testclient import TestClient
from app.main import app


def test_docs_available():
    client = TestClient(app)
    assert client.get("/docs").status_code == 200
