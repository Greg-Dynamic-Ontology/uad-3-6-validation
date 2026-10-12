"""RED acceptance test for IT-2R6S2 reusing a linked local account."""

from types import SimpleNamespace

from fastapi.testclient import TestClient


WORKOS_USER_ID = "user_test_it_2_r6_s2"
CLIENT_ID = "client_test_it_2_r6_s2"
API_KEY = "sk_test_it_2_r6_s2"
COOKIE_PASSWORD = "test-cookie-password"
FIRST_SESSION_COOKIE = "sealed-first-workos-session"
LATER_SESSION_COOKIE = "sealed-later-workos-session"
COMPANY_ID = "company_test_it_2_r6_s2"


def test_it_2_r6_s2_reuses_local_account_after_workos_sign_in(
    monkeypatch,
) -> None:
    """A changed WorkOS email does not create or replace the linked account."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_API_KEY", API_KEY)
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", COOKIE_PASSWORD)
    monkeypatch.setenv(
        "WORKOS_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/callback",
    )

    class FakeAuthenticatedSession:
        def __init__(self, email: str):
            self.email = email

        def authenticate(self):
            return SimpleNamespace(
                authenticated=True,
                user={
                    "id": WORKOS_USER_ID,
                    "email": self.email,
                },
            )

    class FakeUserManagement:
        def load_sealed_session(
            self,
            *,
            session_data: str,
            cookie_password: str,
        ):
            assert cookie_password == COOKIE_PASSWORD

            if session_data == FIRST_SESSION_COOKIE:
                email = "original-s2@example.test"
            elif session_data == LATER_SESSION_COOKIE:
                email = "changed-s2@example.test"
            else:
                raise AssertionError(
                    f"Unexpected WorkOS session cookie: {session_data!r}"
                )

            return FakeAuthenticatedSession(email)

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
    monkeypatch.setitem(
        main.app.state._state,
        "companies",
        {COMPANY_ID: object()},
    )
    monkeypatch.setitem(
        main.app.state._state,
        "authorized_company_ids_by_workos_user",
        {WORKOS_USER_ID: {COMPANY_ID}},
    )

    first_account_data = {
        "user_data": {"display_name": "Alex Example"},
        "company_id": COMPANY_ID,
    }

    with TestClient(main.app, follow_redirects=False) as client:
        client.cookies.set("wos_session", FIRST_SESSION_COOKIE)
        first_response = client.post(
            "/account/setup",
            json=first_account_data,
        )

        assert first_response.status_code == 201, (
            "The first validated WorkOS sign-in should create the local "
            f"account; got HTTP {first_response.status_code}."
        )

        original_account = first_response.json()
        account_id = original_account["user_account_id"]

        client.cookies.set("wos_session", LATER_SESSION_COOKIE)
        later_response = client.post(
            "/account/setup",
            json={
                "user_data": {"display_name": "Changed Name"},
                "company_id": None,
            },
        )

    assert later_response.status_code == 200, (
        "A later sign-in for an already linked WorkOS user should resolve "
        "and reuse the local account; "
        f"got HTTP {later_response.status_code}."
    )
    assert later_response.json() == original_account, (
        "A changed sign-in email or repeated setup request must not replace "
        "the saved account data or company link."
    )
    assert original_account["company_id"] == COMPANY_ID
    assert original_account["account_kind"] == "company_user"

    assert main.app.state.workos_identity_account_links == {
        WORKOS_USER_ID: account_id
    }
    assert list(main.app.state.user_accounts) == [account_id]
    assert main.app.state.user_accounts[account_id].user_data == {
        "display_name": "Alex Example"
    }
    assert main.app.state.user_accounts[account_id].company_id == COMPANY_ID