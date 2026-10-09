"""RED acceptance test for IT-2R5S6 WorkOS callback session creation."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from workos.session import unseal_data


CLIENT_ID = "client_test_it_2_r5_s6"
API_KEY = "sk_test_it_2_r5_s6"
COOKIE_PASSWORD = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
AUTHORIZATION_CODE = "successful-authkit-code"
COOKIE_NAME = "wos_session"

AUTHENTICATED_USER = {
    "id": "user_test_it_2_r5_s6",
    "email": "uad36-s6@example.test",
    "first_name": "S6",
    "last_name": "Test",
}
ACCESS_TOKEN = "test-workos-access-token"
REFRESH_TOKEN = "test-workos-refresh-token"


def test_it_2_r5_s6_establishes_uad_session_after_validating_workos_callback(
    monkeypatch,
) -> None:
    """Validate the callback code and establish a protected UAD session."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_API_KEY", API_KEY)
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", COOKIE_PASSWORD)
    monkeypatch.setenv(
        "WORKOS_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/callback",
    )

    authentication_calls: list[str] = []

    class FakeUserManagement:
        def authenticate_with_code(self, *, code: str):
            authentication_calls.append(code)
            return SimpleNamespace(
                user=SimpleNamespace(
                    to_dict=lambda: dict(AUTHENTICATED_USER)
                ),
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                impersonator=None,
            )

    class FakeWorkOSClient:
        def __init__(self, *, api_key: str | None, client_id: str):
            assert api_key == API_KEY
            assert client_id == CLIENT_ID
            self.user_management = FakeUserManagement()

    from app import main

    monkeypatch.setattr(main, "WorkOSClient", FakeWorkOSClient)

    with TestClient(main.app, follow_redirects=False) as client:
        response = client.get(
            "/auth/callback",
            params={"code": AUTHORIZATION_CODE},
        )

    assert response.status_code in {302, 303}, (
        "A successful WorkOS callback should complete by redirecting after "
        f"session creation; got HTTP {response.status_code}."
    )
    assert authentication_calls == [AUTHORIZATION_CODE], (
        "UAD must validate the callback code through WorkOS before creating "
        "a session."
    )

    session_cookie = response.cookies.get(COOKIE_NAME)
    assert session_cookie, (
        f"A successful callback must set the {COOKIE_NAME} session cookie."
    )

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in set_cookie_header.lower()
    assert "secure" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()

    session_data = unseal_data(session_cookie, COOKIE_PASSWORD)
    assert session_data == {
        "access_token": ACCESS_TOKEN,
        "refresh_token": REFRESH_TOKEN,
        "user": AUTHENTICATED_USER,
    }