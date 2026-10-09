"""RED acceptance test for IT-2R5S5 hosted AuthKit redirection."""

from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient


CLIENT_ID = "client_test_it_2_r5_s5"
CALLBACK_URL = "http://127.0.0.1:8000/auth/callback"


def test_it_2_r5_s5_redirects_unauthenticated_visitor_to_hosted_authkit(
    monkeypatch,
) -> None:
    """Redirect an unauthenticated protected request to hosted AuthKit."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_REDIRECT_URI", CALLBACK_URL)

    from app.main import app

    with TestClient(app, follow_redirects=False) as client:
        response = client.post(
            "/validate/uad36",
            json={
                "package_name": "unauthenticated-appraisal.xml",
                "xml_text": "<APPRAISAL_REPORT/>",
            },
        )

    assert response.status_code in {302, 303, 307, 308}, (
        "An unauthenticated request to protected appraisal validation must "
        f"redirect to hosted AuthKit; got HTTP {response.status_code}."
    )

    location = urlsplit(response.headers["location"])
    assert location.scheme == "https"
    assert location.netloc == "api.workos.com"
    assert location.path == "/user_management/authorize"

    query = parse_qs(location.query)
    assert query.get("provider") == ["authkit"]
    assert query.get("redirect_uri") == [CALLBACK_URL]