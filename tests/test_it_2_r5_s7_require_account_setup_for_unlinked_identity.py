"""RED acceptance test for IT-2R5S7 account setup gating."""

from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app.services.validation import validation_service


WORKOS_USER_ID = "user_test_it_2_r5_s7"
CLIENT_ID = "client_test_it_2_r5_s7"
API_KEY = "sk_test_it_2_r5_s7"
COOKIE_PASSWORD = "test-cookie-password"
SESSION_COOKIE = "sealed-authenticated-workos-session"
AUTHORIZATION_URL = (
    "https://api.workos.com/user_management/authorize"
    "?provider=authkit&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fauth%2Fcallback"
)


def test_it_2_r5_s7_requires_account_setup_for_authenticated_unlinked_identity(
    monkeypatch,
) -> None:
    """An authenticated identity without a UAD link cannot validate appraisals."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_API_KEY", API_KEY)
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", COOKIE_PASSWORD)
    monkeypatch.setenv(
        "WORKOS_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/callback",
    )

    session_loads: list[tuple[str, str]] = []

    class FakeAuthenticatedSession:
        def authenticate(self):
            return SimpleNamespace(
                authenticated=True,
                user={
                    "id": WORKOS_USER_ID,
                    "email": "unlinked-s7@example.test",
                },
            )

    class FakeUserManagement:
        def load_sealed_session(
            self,
            *,
            session_data: str,
            cookie_password: str,
        ):
            session_loads.append((session_data, cookie_password))
            return FakeAuthenticatedSession()

        def get_authorization_url(self, **_kwargs: object) -> str:
            return AUTHORIZATION_URL

    class FakeWorkOSClient:
        def __init__(self, *, api_key: str | None, client_id: str):
            assert api_key == API_KEY
            assert client_id == CLIENT_ID
            self.user_management = FakeUserManagement()

    from app import main

    monkeypatch.setattr(main, "WorkOSClient", FakeWorkOSClient)

    def validation_must_not_run(_request):
        pytest.fail(
            "UAD must require account setup before running appraisal validation."
        )

    monkeypatch.setattr(
        validation_service,
        "validate",
        validation_must_not_run,
    )

    with TestClient(main.app, follow_redirects=False) as client:
        client.cookies.set("wos_session", SESSION_COOKIE)
        response = client.post(
            "/validate/uad36",
            json={
                "package_name": "unlinked-identity-appraisal.xml",
                "xml_text": "<APPRAISAL_REPORT/>",
            },
        )

    assert response.status_code in {302, 303, 307, 308}, (
        "An authenticated identity without a linked UAD account must be "
        f"directed to account setup; got HTTP {response.status_code}."
    )

    destination = urlsplit(response.headers["location"])
    assert destination.path == "/account/setup", (
        "An unlinked authenticated identity must be sent to UAD account setup, "
        f"not another destination: {response.headers['location']!r}."
    )

    assert session_loads == [
        (SESSION_COOKIE, COOKIE_PASSWORD)
    ], "UAD must validate the WorkOS-backed session before deciding account access."