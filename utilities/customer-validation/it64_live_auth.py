"""Real hosted sign-in support. Session state stays in memory for this pytest run."""
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit
import pytest

_SESSION = None
_SESSION_KEY = None

def visible_sign_in_required(config):
    if not config.getoption("headed", default=False):
        pytest.fail("IT-64 hosted sign-in is interactive. Run utilities/customer-validation/run_it64_tests.py; it uses --headed -s. Keep the server running in its own terminal.", pytrace=False)

def session_state(profile, base):
    key = (base, profile["user_account_id"])
    return _SESSION if key == _SESSION_KEY else {"cookies": [], "origins": []}

def remember_session(page, profile, base):
    global _SESSION, _SESSION_KEY
    response = page.context.request.get(base + "/account/context")
    assert response.status == 200 and response.json()["user_account_id"] == profile["user_account_id"], "Only a genuinely authenticated matching user session may be reused."
    _SESSION = page.context.storage_state()
    _SESSION_KEY = (base, profile["user_account_id"])

def wait_for_verified_account(page, profile, base):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        location = urlsplit(page.url)
        if location.path == "/redirect-uri-invalid":
            pytest.fail("WorkOS rejected the callback. Register exactly " + base + "/auth/callback in the application matching the server Client ID, then start sign-in again from /login.", pytrace=False)
        if location.netloc == urlsplit(base).netloc and location.path == "/auth/callback":
            pytest.fail("UAD authentication callback did not complete. Inspect the server callback error; verify the API key and Client ID belong to the same WorkOS environment.", pytrace=False)
        if location.netloc == urlsplit(base).netloc:
            response = page.context.request.get(base + "/account/context")
            if response.status == 200:
                assert response.json()["user_account_id"] == profile["user_account_id"], "Sign in as the designated test-profile user."
                remember_session(page, profile, base)
                return
            if response.status != 401:
                pytest.fail(f"Hosted sign-in returned to UAD but account linkage/authorization failed (HTTP {response.status}): {response.text()}", pytrace=False)
        page.wait_for_timeout(250)
    location = urlsplit(page.url)
    pytest.fail("Hosted sign-in did not complete. Current page: " + location.netloc + location.path + ". Complete the password and emailed verification code in the visible test browser; Outlook must already receive the designated user's email. No authentication was bypassed.", pytrace=False)

def sign_in(page, profile, base):
    response = page.context.request.get(base + "/account/context")
    if response.status == 200:
        assert response.json()["user_account_id"] == profile["user_account_id"]
        return
    print("Complete real WorkOS password/email verification in this visible browser. Session reuse is in memory only.", flush=True)
    page.goto(base + "/login", wait_until="domcontentloaded")
    wait_for_verified_account(page, profile, base)

def cycle_baseline(profile):
    root = Path(__file__).resolve().parents[1]
    store = Path(os.environ.get("UAD_CUSTOMER_STORE", str(root / "data/customer-validation.sqlite3"))).resolve()
    assert store.is_file(), f"Use the initialized store shared with the running server: {store}"
    with sqlite3.connect(store.as_uri() + "?mode=ro", uri=True) as db:
        return [row[0] for row in db.execute("SELECT validation_cycle_id FROM account_validation_cycles WHERE customer_account_id=?", (profile["customer_account_id"],))]
