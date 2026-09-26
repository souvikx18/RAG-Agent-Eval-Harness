from fastapi.testclient import TestClient
from test_agent import app

client = TestClient(app)


def test_local_test_agent_health():
    """Verify health endpoint returns 200 OK with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_test_agent_run():
    """Verify POST /agent accepts input and returns structured output."""
    response = client.post("/agent", json={"input": "Hello Veridyn"})
    assert response.status_code == 200
    assert response.json() == {
        "output": "Hello! I received your message: Hello Veridyn"
    }


def test_local_test_agent_empty_input():
    """Verify POST /agent handles empty input string."""
    response = client.post("/agent", json={"input": ""})
    assert response.status_code == 200
    assert response.json() == {
        "output": "Hello! I received your message: "
    }


def test_local_test_agent_invalid_payload():
    """Verify POST /agent rejects malformed payload with 422 Unprocessable Entity."""
    response = client.post("/agent", json={"invalid_field": 123})
    assert response.status_code == 422
