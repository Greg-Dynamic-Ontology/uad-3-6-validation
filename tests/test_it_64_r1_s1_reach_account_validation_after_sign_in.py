"""IT-64R1S1: reach account validation through real browser authentication.

Run against a dedicated, already running UAD test server with --headed -s.
Complete the real hosted sign-in in the visible browser when it opens.
No authentication, account, lifecycle, or storage responses are mocked.

Set UAD_IT64_CUSTOMER_PROFILE to a JSON profile containing independently known
test-user/account expectations. The account, verified identity link, active
membership, and authorized mode are preconditions, not created by this test.
The profile contains no password, API key, session cookie, or access token.

Proposed observable integration contract:
- The landing page has a visible Sign in link/button.
- The existing /auth/callback completes hosted authentication.
- /validation/?customer_account_id=... renders #authenticated-user with
  data-user-account-id, #selected-customer-account with data-customer-account-id,
  and #operating-mode with data-operating-mode. Names and mode are visible.
- An enabled New validation cycle link/button is offered.
- GET /validation-cycles?customer_account_id=... returns customer_account_id
  and cycles, whose entries contain validation_cycle_id. The dedicated test
  account's complete cycle inventory is compared with its independent baseline.

The current application is expected to fail at the missing browser Sign in
entry. A missing profile later is setup RED, not evidence of a product defect.
This is an interactive integration test, not an unattended sign-in test.
"""

import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect


def _profile() -> dict:
    location = os.environ.get("UAD_IT64_CUSTOMER_PROFILE")
    if not location:
        pytest.fail(
            "IT-64R1S1 setup: set UAD_IT64_CUSTOMER_PROFILE to the completed "
            "test-account JSON profile. Do not put credentials in that file.",
            pytrace=False,
        )
    path = Path(location).expanduser()
    if not path.is_file():
        pytest.fail(f"IT-64R1S1 test-account profile not found: {path}", pytrace=False)
    profile = json.loads(path.read_text(encoding="utf-8-sig"))
    assert isinstance(profile, dict)
    for field in (
        "user_account_id", "display_name", "customer_account_id",
        "customer_account_label", "operating_mode", "hosted_sign_in_hostname",
    ):
        assert isinstance(profile.get(field), str) and profile[field].strip(), (
            f"IT-64R1S1 setup: supply the independently known {field}."
        )
        assert not profile[field].startswith("REPLACE_"), (
            f"IT-64R1S1 setup: replace the {field} example with the real test-account value."
        )
    assert profile["operating_mode"] in {"standard", "developer"}
    cycles = profile.get("preexisting_cycle_ids")
    assert isinstance(cycles, list) and all(isinstance(item, str) and item for item in cycles)
    assert len(set(cycles)) == len(cycles)
    return profile


def test_it_64_r1_s1_reaches_account_validation_after_successful_sign_in(page: Page) -> None:
    base_url = os.environ.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    origin = urlsplit(base_url)
    assert origin.scheme in {"http", "https"} and origin.netloc
    try:
        response = page.goto(base_url + "/", wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        pytest.fail(f"IT-64R1S1 could not load the running test application at {base_url}.", pytrace=False)
    assert response is not None and response.ok
    sign_in = page.get_by_role("link", name=re.compile(r"^sign in$", re.I)).or_(
        page.get_by_role("button", name=re.compile(r"^sign in$", re.I))
    ).first
    expect(sign_in).to_be_visible(timeout=5000)
    expect(sign_in).to_be_enabled()

    # Resolve the application entry before checking external test-account setup,
    # so the first RED identifies the currently missing browser integration.
    profile = _profile()
    hosted_visits = []
    callback_responses = []
    prohibited_validation_requests = []

    def record_navigation(frame):
        if frame == page.main_frame:
            hosted_visits.append(urlsplit(frame.url).hostname)

    def record_response(result):
        location = urlsplit(result.url)
        if location.netloc == origin.netloc and location.path == "/auth/callback":
            callback_responses.append(result.status)

    def record_request(request):
        location = urlsplit(request.url)
        if location.netloc != origin.netloc or request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return
        if location.path.startswith(("/validation-cycles", "/validate/")):
            prohibited_validation_requests.append((request.method, location.path))

    page.on("framenavigated", record_navigation)
    page.on("response", record_response)
    page.on("request", record_request)
    try:
        print("Complete sign-in with the designated WorkOS test account in the visible browser.")
        sign_in.click()
        page.wait_for_function(
            "() => document.querySelector('#authenticated-user')?.getAttribute('data-user-account-id') === "
            + json.dumps(profile["user_account_id"]),
            timeout=180000,
        )
        assert profile["hosted_sign_in_hostname"] in hosted_visits, (
            "The browser must pass through the configured real hosted sign-in service."
        )
        assert any(status in {200, 302, 303} for status in callback_responses), (
            "The existing UAD authentication callback must complete over the network."
        )

        query = urlencode({"customer_account_id": profile["customer_account_id"]})
        response = page.goto(base_url + "/validation/?" + query, wait_until="domcontentloaded")
        assert response is not None and response.ok

        user = page.locator("#authenticated-user")
        expect(user).to_be_visible()
        expect(user).to_have_attribute("data-user-account-id", profile["user_account_id"])
        expect(user).to_contain_text(profile["display_name"])
        account = page.locator("#selected-customer-account")
        expect(account).to_be_visible()
        expect(account).to_have_attribute("data-customer-account-id", profile["customer_account_id"])
        expect(account).to_contain_text(profile["customer_account_label"])
        mode = page.locator("#operating-mode")
        expect(mode).to_be_visible()
        expect(mode).to_have_attribute("data-operating-mode", profile["operating_mode"])
        expect(mode).to_contain_text(re.compile(profile["operating_mode"], re.I))
        assert page.locator(".demo-mode-indicator:visible").count() == 0
        assert page.get_by_role("status", name=re.compile(r"^demo mode$", re.I)).count() == 0

        new_cycle = page.get_by_role("link", name=re.compile(r"^new validation cycle$", re.I)).or_(
            page.get_by_role("button", name=re.compile(r"^new validation cycle$", re.I))
        ).first
        expect(new_cycle).to_be_visible()
        expect(new_cycle).to_be_enabled()
        # Do not activate it: sign-in and page viewing must create no cycle.
        result = page.request.get(base_url + "/validation-cycles?" + query)
        assert result.status == 200, "The account's cycle inventory must be retrievable after sign-in."
        inventory = result.json()
        assert inventory.get("customer_account_id") == profile["customer_account_id"]
        cycles = inventory.get("cycles")
        assert isinstance(cycles, list)
        actual_ids = [cycle["validation_cycle_id"] for cycle in cycles]
        assert len(actual_ids) == len(set(actual_ids))
        assert set(actual_ids) == set(profile["preexisting_cycle_ids"]), (
            "Sign-in and viewing account validation must leave the independently "
            "recorded cycle inventory unchanged."
        )
        assert not prohibited_validation_requests, (
            "Sign-in and viewing the page must not initiate validation or create a cycle."
        )
    finally:
        page.remove_listener("framenavigated", record_navigation)
        page.remove_listener("response", record_response)
        page.remove_listener("request", record_request)
