from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_page_presents_phase_one_service_shell() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "UAD 3.6 Validation" in response.text
    assert "Version 0.1" in response.text
    assert "Run Validation" in response.text
    assert 'href="/validation/"' in response.text
    assert "Documentation" in response.text
    assert 'href="/docs"' in response.text
    assert 'fetch("/health"' in response.text


def test_health_endpoint_supports_home_page_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "uad_version": "3.6",
    }
