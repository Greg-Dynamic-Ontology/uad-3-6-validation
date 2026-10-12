"""IT-2R6S3: reject identity links supplied by the client."""

from types import SimpleNamespace

from fastapi.testclient import TestClient


AUTHENTICATED_WORKOS_USER_ID = "user_verified_it_2_r6_s3"
CLIENT_SUPPLIED_WORKOS_USER_ID = "user_client_supplied_it_2_r6_s3"
CLIENT_ID = "client_test_it_2_r6_s3"
API_KEY = "sk_test_it_2_r6_s3"
COOKIE_PASSWORD = "test-cookie-password"
SESSION_COOKIE = "sealed-authenticated-workos-session"


def test_it_2_r6_s3_rejects_client_supplied_workos_identity_link(
    monkeypatch,
) -> None:
    """A client cannot choose which WorkOS identity gets linked."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_API_KEY", API_KEY)
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", COOKIE_PASSWORD)

    class FakeAuthenticatedSession:
        def authenticate(self):
            return SimpleNamespace(
                authenticated=True,
                user={
                    "id": AUTHENTICATED_WORKOS_USER_ID,
                    "email": "verified-s3@example.test",
                },
            )

    class FakeUserManagement:
        def load_sealed_session(
            self,
            *,
            session_data: str,
            cookie_password: str,
        ):
            assert session_data == SESSION_COOKIE
            assert cookie_password == COOKIE_PASSWORD
            return FakeAuthenticatedSession()

    class FakeWorkOSClient:
        def __init__(self, *, api_key: str | None, client_id: str):
            assert api_key == API_KEY
            assert client_id == CLIENT_ID
            self.user_management = FakeUserManagement()

    from app import main

    monkeypatch.setitem(main.__dict__, "WorkOSClient", FakeWorkOSClient)
    monkeypatch.setitem(
        main.app.state._state,
        "workos_identity_account_links",
        {},
    )
    monkeypatch.setitem(
        main.app.state._state,
        "user_accounts",
        {},
    )

    with TestClient(main.app, follow_redirects=False) as client:
        client.cookies.set("wos_session", SESSION_COOKIE)
        response = client.post(
            "/account/setup",
            json={
                "user_data": {"display_name": "Alex Example"},
                "company_id": None,
                "workos_user_id": CLIENT_SUPPLIED_WORKOS_USER_ID,
            },
        )

    assert response.status_code == 422, (
        "The account setup request must reject a client-supplied WorkOS "
        f"identity; got HTTP {response.status_code}."
    )
    assert main.app.state.workos_identity_account_links == {}, (
        "Rejecting a client-supplied identity must leave identity links "
        "unchanged."
    )
    assert main.app.state.user_accounts == {}, (
        "Rejecting a client-supplied identity must leave local accounts "
        "unchanged."
    )