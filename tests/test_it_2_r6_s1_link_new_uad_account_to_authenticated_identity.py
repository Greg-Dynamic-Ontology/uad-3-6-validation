"""RED acceptance test for IT-2R6S1 WorkOS identity-to-account linking."""

from types import SimpleNamespace

from fastapi.testclient import TestClient


WORKOS_USER_ID = "user_test_it_2_r6_s1"
CLIENT_ID = "client_test_it_2_r6_s1"
API_KEY = "sk_test_it_2_r6_s1"
COOKIE_PASSWORD = "test-cookie-password"
SESSION_COOKIE = "sealed-authenticated-workos-session"


def test_it_2_r6_s1_links_new_uad_account_to_authenticated_workos_identity(
    monkeypatch,
) -> None:
    """Account setup creates one local account linked to the session identity."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_API_KEY", API_KEY)
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", COOKIE_PASSWORD)
    monkeypatch.setenv(
        "WORKOS_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/callback",
    )

    class FakeAuthenticatedSession:
        def authenticate(self):
            return SimpleNamespace(
                authenticated=True,
                user={
                    "id": WORKOS_USER_ID,
                    "email": "new-account-s1@example.test",
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

    account_data = {
        "user_data": {"display_name": "Alex Example"},
        "company_id": None,
    }

    with TestClient(main.app, follow_redirects=False) as client:
        client.cookies.set("wos_session", SESSION_COOKIE)
        response = client.post("/account/setup", json=account_data)

    assert response.status_code == 201, (
        "Completing account setup for a validated WorkOS identity should "
        f"create a local account; got HTTP {response.status_code}."
    )

    created_account = response.json()
    account_id = created_account.get("user_account_id")
    assert account_id, "The created local account must have an identifier."
    assert created_account.get("user_data") == account_data["user_data"]
    assert created_account.get("company_id") is None
    assert created_account.get("account_kind") == "single_user"
    assert "password" not in created_account
    assert "password_hash" not in created_account

    assert main.app.state.workos_identity_account_links == {
        WORKOS_USER_ID: account_id
    }, (
        "The new local account must be linked to the WorkOS user ID from "
        "the validated session."
    )