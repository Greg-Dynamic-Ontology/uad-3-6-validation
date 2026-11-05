"""IT-64R1S3: anonymous account-cycle entry must offer real sign-in.

Run against the actual port-4000 server with WorkOS configured. No manual
sign-in is needed: stop at the hosted authentication page. No response or
authentication is mocked. A deliberately invalid cookie is negative input.

Proposed browser contract: opening the existing account-scoped /validation/
entry must either start /login or display an actionable Sign in link/button.
A bare JSON 401 is access denial but does not provide the required browser flow.
Cycle creation/submission execution remains for later IT-64 scenarios.

Use the same UAD_CUSTOMER_STORE as an otherwise idle local test server. When
UAD_IT64_CUSTOMER_PROFILE is supplied, its actual account ID is used; otherwise
an explicitly untrusted account reference tests rejection before account lookup.
Storage checks cover the configured customer SQLite store, not external stores.
"""

import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlencode, urlsplit

import pytest
from playwright.sync_api import Browser, Error as PlaywrightError, expect


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _snapshot(path: Path):
    if not path.exists():
        return None
    assert path.is_file(), f"IT-64R1S3 setup: customer-store path is not a file: {path}"
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("BEGIN")
        names = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        # Security audit entries may legitimately record the denied attempt.
        protected = {}
        for name in names:
            if name == "entry_audit":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            protected[name] = (
                tuple(connection.execute(f"PRAGMA table_info({quoted})").fetchall()),
                tuple(sorted(connection.execute(f"SELECT * FROM {quoted}").fetchall(), key=repr)),
            )
        return protected
    finally:
        connection.close()


def _account_id() -> str:
    location = os.environ.get("UAD_IT64_CUSTOMER_PROFILE")
    if not location:
        return "untrusted-it64r1s3-account-reference"
    path = Path(location).expanduser()
    assert path.is_file(), f"IT-64R1S3 setup: profile not found: {path}"
    account_id = json.loads(path.read_text(encoding="utf-8-sig")).get("customer_account_id")
    assert isinstance(account_id, str) and account_id.strip() and not account_id.startswith("REPLACE_"), (
        "IT-64R1S3 setup: profile must identify the actual test account."
    )
    return account_id


@pytest.mark.parametrize("session_state", ["absent-session", "invalid-session"])
def test_it_64_r1_s3_requires_browser_sign_in_before_account_owned_cycle(
    browser: Browser, session_state: str,
) -> None:
    base_url = os.environ.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    origin = urlsplit(base_url)
    assert origin.scheme in {"http", "https"} and origin.netloc
    store = Path(os.environ.get(
        "UAD_CUSTOMER_STORE", str(PROJECT_ROOT / "data" / "customer-validation.sqlite3")
    )).expanduser().resolve()
    before = _snapshot(store)
    query = urlencode({"customer_account_id": _account_id()})
    context = browser.new_context(storage_state={"cookies": [], "origins": []})
    if session_state == "invalid-session":
        context.add_cookies([{
            "name": "wos_session", "value": "deliberately-invalid-it64r1s3-session",
            "url": base_url, "httpOnly": True, "sameSite": "Lax",
        }])
    page = context.new_page()
    login_responses = []
    protected_mutations = []

    def record_response(response):
        location = urlsplit(response.url)
        if location.netloc == origin.netloc and location.path == "/login":
            login_responses.append(response)

    def record_request(request):
        location = urlsplit(request.url)
        if location.netloc != origin.netloc:
            return
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if location.path.startswith(("/validation", "/validate/", "/account/")):
                protected_mutations.append((request.method, location.path))

    page.on("response", record_response)
    page.on("request", record_request)
    try:
        try:
            # This is the real browser entry to requesting a new account-owned
            # cycle, not an invented cycle-creation API or a Demo submission.
            response = page.goto(base_url + "/validation/?" + query, wait_until="domcontentloaded")
        except PlaywrightError:
            pytest.fail(
                f"IT-64R1S3 setup: cannot load the running application at {base_url}. "
                "Keep the WorkOS-configured UAD server running.", pytrace=False,
            )
        assert response is not None
        assert response.status < 500, "Account entry must handle an absent or invalid session without a server error."

        # Inspect access denial and persistent side effects before checking the
        # browser recovery action, so a sign-in link cannot hide data disclosure.
        denied = context.request.get(base_url + "/validation-cycles?" + query, max_redirects=0)
        assert denied.status in {401, 403}, (
            "IT-64R1S3: unauthenticated account history must be denied by the real API."
        )
        assert "application/json" in denied.headers.get("content-type", "")
        payload = denied.json()
        assert isinstance(payload, dict) and "detail" in payload
        assert not ({"cycles", "submissions", "results", "history", "findings"} & payload.keys()), (
            "IT-64R1S3: an authentication diagnostic must not include customer history."
        )
        if urlsplit(page.url).netloc == origin.netloc:
            assert page.locator("#authenticated-user:visible").count() == 0
            assert page.locator("#selected-customer-account:visible").count() == 0
            assert page.locator("#new-cycle-action:visible").count() == 0
            sign_in = page.get_by_role("link", name=re.compile(r"^sign in$", re.I)).or_(
                page.get_by_role("button", name=re.compile(r"^sign in$", re.I))
            ).first
            assert sign_in.count() > 0, (
                "IT-64R1S3 requires account-cycle browser entry without a valid session "
                "to start the existing /login flow or display an actionable Sign in control. "
                "A bare unauthorized JSON response does not provide browser sign-in."
            )
            expect(sign_in).to_be_visible()
            expect(sign_in).to_be_enabled()
            sign_in.click()

        page.wait_for_url(lambda url: urlsplit(str(url)).netloc != origin.netloc, timeout=30000)
        assert login_responses, "The browser must use the existing /login endpoint to initiate hosted sign-in."
        assert any(result.status in {302, 303, 307} for result in login_responses), (
            "The existing sign-in entry must issue a real hosted-authentication redirect."
        )
        destination = urlsplit(page.url)
        assert destination.scheme == "https" and destination.hostname
        assert "redirect-uri-invalid" not in destination.path, (
            "IT-64R1S3 setup: register the callback in the same WorkOS test application."
        )
        assert not protected_mutations, (
            "IT-64R1S3: unauthenticated entry must not create a cycle, submit a report, "
            f"or create account records: {protected_mutations}"
        )
    finally:
        context.close()
        assert _snapshot(store) == before, (
            "IT-64R1S3: the sign-in challenge changed protected customer records, "
            "including account-owned cycles or submissions."
        )
