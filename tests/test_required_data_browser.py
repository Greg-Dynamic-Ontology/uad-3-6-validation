"""Browser acceptance tests for Required Data Validation."""

import re
import socket
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    ROOT / "data/uad36-test-suite/tests/fixtures/required_data"
)

CLIENT_ID = "client_test_required_data_browser"
API_KEY = "sk_test_required_data_browser"
COOKIE_PASSWORD = "test-required-data-browser-cookie-password"
SESSION_COOKIE = "sealed-required-data-browser-session"
WORKOS_USER_ID = "user_test_required_data_browser"
AUTHORIZATION_URL = (
    "https://api.workos.com/user_management/authorize"
    "?provider=authkit"
    "&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fauth%2Fcallback"
)


class FakeAuthenticatedSession:
    def authenticate(self):
        return SimpleNamespace(
            authenticated=True,
            user={
                "id": WORKOS_USER_ID,
                "email": "required-data-browser@example.test",
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

    def get_authorization_url(self, **_kwargs: object) -> str:
        return AUTHORIZATION_URL


class FakeWorkOSClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        client_id: str,
    ):
        assert api_key == API_KEY
        assert client_id == CLIENT_ID
        self.user_management = FakeUserManagement()


@pytest.fixture
def required_data_server_url(
    monkeypatch: pytest.MonkeyPatch,
    page: Page,
):
    import app.main as main

    previous_configuration = app.state.configuration_file
    previous_links = dict(
        app.state.workos_identity_account_links
    )

    monkeypatch.setenv("WORKOS_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("WORKOS_API_KEY", API_KEY)
    monkeypatch.setenv("WORKOS_COOKIE_PASSWORD", COOKIE_PASSWORD)
    monkeypatch.setenv(
        "WORKOS_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/callback",
    )
    monkeypatch.setattr(main, "WorkOSClient", FakeWorkOSClient)

    app.state.configuration_file = (
        ROOT / "config/configuration.developer.ttl"
    )
    app.state.workos_identity_account_links = {
        WORKOS_USER_ID: "uad-test-account-required-data-browser"
    }

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 0))
    host, port = server_socket.getsockname()
    server_url = f"http://{host}:{port}"

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="error",
            ws="none",
        )
    )
    thread = Thread(
        target=server.run,
        kwargs={"sockets": [server_socket]},
        daemon=True,
    )

    try:
        thread.start()
        deadline = monotonic() + 10
        while not server.started and monotonic() < deadline:
            sleep(0.01)

        if not server.started:
            pytest.fail("The local validation server did not start.")

        page.context.add_cookies(
            [
                {
                    "name": "wos_session",
                    "value": SESSION_COOKIE,
                    "url": server_url,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ]
        )

        yield server_url
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        server_socket.close()
        app.state.configuration_file = previous_configuration
        app.state.workos_identity_account_links = previous_links


@pytest.mark.parametrize(
    "relative_file, expected_fatal_count",
    [
        ("baseline/SF1_Appraisal_v1.4.xml", 0),
        (
            "tests/0100.0007-UAD1001-missing-AddressLineText.xml",
            1,
        ),
    ],
    ids=["complete-baseline", "missing-subject-address"],
)
def test_required_data_upload(
    page: Page,
    required_data_server_url: str,
    relative_file: str,
    expected_fatal_count: int,
    required_data_baseline_clock,
):
    source = FIXTURES / relative_file
    assert source.is_file(), f"Missing fixture: {source}"

    page.goto(f"{required_data_server_url}/validation/")

    option = page.get_by_role(
        "radio",
        name="Required Data Validation",
        exact=True,
    )
    expect(option).to_be_visible()
    expect(option).to_be_enabled()
    option.check()

    page.locator("#appraisal-file").set_input_files(str(source))

    with page.expect_response(
        lambda response: (
            response.request.method == "POST"
            and "/validate/uad36" in response.url
        )
    ) as pending:
        page.locator("#validate-button").click()

    response = pending.value
    assert response.status == 200, response.text()
    report = response.json()

    assert report["summary"]["fatal"] == expected_fatal_count
    assert report["summary"]["error"] == 0

    results = page.locator("#validation-results-content")
    expect(results).to_be_visible()
    expect(results).to_contain_text("Required Data Validation")

    if expected_fatal_count:
        assert len(report["findings"]) == 1
        finding = report["findings"][0]
        assert finding["rule_id"] == "UAD1001"
        assert finding["row_id"] == "0100.0007"
        assert finding["severity"] == "fatal"

        expect(results).to_contain_text("UAD1001")
        expect(results).to_contain_text("0100.0007")
        expect(results).to_contain_text(
            re.compile(r"\bfatal\b", re.IGNORECASE)
        )
        expect(results).to_contain_text(finding["finding"])
    else:
        assert report["findings"] == []
        expect(results).to_contain_text(
            "No required-data findings"
        )