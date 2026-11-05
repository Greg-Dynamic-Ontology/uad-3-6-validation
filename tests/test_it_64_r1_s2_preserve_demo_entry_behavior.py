"""IT-64R1S2: preserve IT-25 Demo entry through the running application.

Uses a fresh anonymous browser, real HTTP, the published SF1 report, and a
read-only snapshot of the configured customer SQLite store. No authentication,
validation, or storage responses are mocked. Run against an otherwise idle
dedicated local test server using the same UAD_CUSTOMER_STORE as this process.
No customer-account provisioning is required for an anonymous Demo visitor.
An absent customer store is recorded as absent and must remain absent.

The snapshot covers all tables in that customer store, including any credit
tables present there. It does not claim to inspect unrelated external stores.
Do not add test-only endpoints or fabricate a failure if this is already GREEN.
"""

import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import Browser, Error as PlaywrightError, expect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = (
    PROJECT_ROOT / "specs" / "fannie-mae"
    / "Appendix D-1 SF1_Appraisal" / "SF1_Appraisal_v1.4.xml"
)


def _store_snapshot(path: Path) -> dict[str, tuple] | None:
    """Read committed records without creating a database or schema."""
    if not path.exists():
        return None
    assert path.is_file(), f"IT-64R1S2 setup: configured customer store is not a file: {path}"
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("BEGIN")
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        required = {"entry_users", "entry_accounts", "entry_memberships", "account_validation_cycles"}
        assert required.issubset(tables), "IT-64R1S2 setup: use the actual initialized customer-entry store."
        snapshot = {}
        for name in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            columns = tuple(connection.execute(f"PRAGMA table_info({quoted})").fetchall())
            rows = tuple(sorted(connection.execute(f"SELECT * FROM {quoted}").fetchall(), key=repr))
            snapshot[name] = (columns, rows)
        return snapshot
    finally:
        connection.close()


def test_it_64_r1_s2_preserves_demo_entry_without_account_or_credit_effects(browser: Browser) -> None:
    base_url = os.environ.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    origin = urlsplit(base_url)
    assert origin.scheme in {"http", "https"} and origin.netloc
    store_path = Path(os.environ.get(
        "UAD_CUSTOMER_STORE", str(PROJECT_ROOT / "data" / "customer-validation.sqlite3")
    )).expanduser().resolve()
    report_path = Path(os.environ.get("UAD_IT64_DEMO_REPORT", str(DEFAULT_REPORT))).expanduser().resolve()
    assert report_path.is_file(), f"IT-64R1S2 setup: published Demo report not found: {report_path}"
    before = _store_snapshot(store_path)
    mutations = []
    forbidden_requests = []
    # Explicit empty state prevents accidental reuse of the signed-in R1S1 user.
    context = browser.new_context(storage_state={"cookies": [], "origins": []})
    page = context.new_page()

    def record_request(request):
        location = urlsplit(request.url)
        if location.netloc != origin.netloc:
            return
        query = parse_qs(location.query)
        if "customer_account_id" in query:
            forbidden_requests.append((request.method, location.path))
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            mutations.append((request.method, location.path))
            if not location.path.startswith("/validate/"):
                forbidden_requests.append((request.method, location.path))

    page.on("request", record_request)
    try:
        try:
            response = page.goto(base_url + "/", wait_until="networkidle")
        except PlaywrightError:
            pytest.fail(
                f"IT-64R1S2 setup: cannot load the running UAD server at {base_url}. "
                "Start utilities/customer-validation/run_server.py before this test.",
                pytrace=False,
            )
        assert response is not None and response.status == 200
        indicator = page.locator(".demo-mode-indicator")
        expect(indicator).to_be_visible()
        expect(indicator).to_have_text(re.compile(r"^Demo Mode$", re.I))
        disclosure = page.get_by_role("dialog", name="Continue in Demo Mode?")
        expect(disclosure).to_be_visible()
        for explanation in (
            "Demo mode does not provide customer-owned validation cycles.",
            "Demo mode does not retain account validation history.",
            "Demo mode does not support corrected submissions within an existing cycle.",
            "Demo mode does not purchase, hold, or consume account credits.",
        ):
            expect(disclosure).to_contain_text(explanation)
        expect(disclosure.get_by_role("button", name="Cancel", exact=True)).to_be_visible()
        expect(disclosure.get_by_role("button", name="Continue in Demo Mode", exact=True)).to_be_visible()

        # Cancel must close locally and leave the visitor on the landing page.
        landing_url = page.url
        disclosure.get_by_role("button", name="Cancel", exact=True).click()
        expect(disclosure).not_to_be_visible()
        expect(page).to_have_url(landing_url)
        expect(indicator).to_be_visible()
        assert not mutations, "IT-64R1S2: cancel must not submit, validate, or create account resources."
        assert _store_snapshot(store_path) == before, "IT-64R1S2: cancellation changed customer records."

        # Run Validation must request Demo consent again after cancellation.
        page.get_by_role("link", name="Run Validation", exact=True).click()
        expect(disclosure).to_be_visible()
        disclosure.get_by_role("button", name="Continue in Demo Mode", exact=True).click()
        page.wait_for_url(re.compile(re.escape(base_url) + r"/validation/?$"))
        page.wait_for_load_state("networkidle")
        expect(page.locator(".demo-mode-indicator")).to_be_visible()
        expect(page.locator("#technical-pipeline-selection")).to_be_hidden()
        expect(page.locator("#appraisal-file")).to_be_visible()
        expect(page.get_by_role("button", name="Validate Appraisal", exact=True)).to_be_enabled()
        assert page.locator("#authenticated-user:visible").count() == 0
        assert page.locator("#selected-customer-account:visible").count() == 0
        assert page.locator('[name="customer_account_id"]').count() == 0
        assert not mutations, "IT-64R1S2: continuing into Demo must not initiate validation or account creation."

        # Actual Demo execution, not just inspecting static HTML.
        page.locator("#appraisal-file").set_input_files(str(report_path))
        with page.expect_response(
            lambda result: urlsplit(result.url).netloc == origin.netloc
            and urlsplit(result.url).path.startswith("/validate/")
            and result.request.method == "POST",
            timeout=120000,
        ) as submitted:
            page.get_by_role("button", name="Validate Appraisal", exact=True).click()
        result = submitted.value
        assert result.status == 200, (
            f"IT-64R1S2: the existing Demo validation must remain usable; got HTTP {result.status}."
        )
        assert isinstance(result.json(), dict), "The actual Demo service must return its result."
        expect(page.locator("#validation-results-content")).to_contain_text(report_path.name, timeout=120000)
        expect(page.locator(".demo-mode-indicator")).to_be_visible()
        expect(page.get_by_role("button", name="Validate Appraisal", exact=True)).to_be_enabled(timeout=120000)
        assert not forbidden_requests, (
            "IT-64R1S2: anonymous Demo sent an account-scoped or account-mutating request: "
            f"{forbidden_requests}"
        )

        # The server must still regard this browser as anonymous after Demo use.
        account_response = context.request.get(base_url + "/account/context")
        assert account_response.status == 401, (
            "IT-64R1S2: Demo continuation must not establish an authenticated customer account."
        )
        assert not any(cookie["name"] == "wos_session" for cookie in context.cookies(base_url))
        assert _store_snapshot(store_path) == before, (
            "IT-64R1S2: Demo entry or execution changed customer users, memberships, "
            "cycles, credit records, or other durable customer-store records."
        )
    finally:
        context.close()
