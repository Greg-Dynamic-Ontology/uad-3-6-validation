"""IT-63R1S1: expose service health through the application's HTTP API."""

from fastapi.testclient import TestClient

from app.main import app


def test_it_63_r1_s1_returns_successful_service_health_response() -> None:
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/health")

    assert response.status_code == 200, (
        "IT-63R1S1 requires GET /health to return a successful health "
        f"response; got HTTP {response.status_code}: {response.text}"
    )
    assert response.headers.get("content-type", "").startswith("application/json"), (
        "The health endpoint must return a machine-readable JSON response."
    )
    payload = response.json()
    assert isinstance(payload, dict), "The health response must be a JSON object."
    assert payload.get("status") == "ok", (
        "IT-63R1S1 requires the response to identify the healthy service "
        f"state as status='ok'; received {payload!r}."
    )
