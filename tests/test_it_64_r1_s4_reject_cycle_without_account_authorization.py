"""IT-64R1S4: signed-in identity cannot bypass account validation permission.

Actual browser WorkOS sign-in followed by real HTTP API requests. No auth,
worker, or storage responses are mocked. Complete hosted sign-in within 3 min.
Use an otherwise idle dedicated local test server and the same UAD_CUSTOMER_STORE.

Fixture setup inserts a temporary owner-only account for the existing test user.
It never changes the user's existing account or roles. The protected-state
baseline is taken AFTER this setup. Unchanged fixture records are removed at
the end; unexpected mutations are preserved for investigation. Storage checks
cover all non-audit tables in this customer store, not unrelated external stores.

Proposed POST /validation-cycles JSON: customer_account_id, package_name,
xml_text; Idempotency-Key identifies the request. The account query parameter
also exercises selection conflicts. Authorization must precede validation work.
A 404/405 or input-validation error is not the required authorization denial.
"""

import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from tests.it64_live_auth import visible_sign_in_required, session_state, sign_in, wait_for_verified_account, cycle_baseline

from playwright.sync_api import Browser


ROOT = Path(__file__).resolve().parents[1]


def _snapshot(connection):
    names = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    snapshot = {}
    for name in names:
        if name == "entry_audit":
            continue
        quoted = '"' + name.replace('"', '""') + '"'
        snapshot[name] = (
            tuple(connection.execute(f"PRAGMA table_info({quoted})").fetchall()),
            tuple(sorted(connection.execute(f"SELECT * FROM {quoted}").fetchall(), key=repr)),
        )
    return snapshot


def test_it_64_r1_s4_denies_cycle_creation_without_account_validation_permission(browser: Browser, pytestconfig) -> None:
    visible_sign_in_required(pytestconfig)
    base = os.environ.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    profile_path = Path(os.environ.get(
        "UAD_IT64_CUSTOMER_PROFILE", str(ROOT / "tests/fixtures/it_64/r1/s1/customer-profile.json")
    )).expanduser()
    assert profile_path.is_file(), f"IT-64R1S4 setup: completed account profile required: {profile_path}"
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    for key in ("user_account_id", "customer_account_id", "hosted_sign_in_hostname"):
        assert isinstance(profile.get(key), str) and profile[key] and not profile[key].startswith("REPLACE_"), (
            f"IT-64R1S4 setup: supply the real {key}."
        )
    store = Path(os.environ.get("UAD_CUSTOMER_STORE", str(ROOT / "data/customer-validation.sqlite3"))).expanduser().resolve()
    assert store.is_file(), f"IT-64R1S4 setup: use the real initialized test-account store: {store}"
    report = ROOT / "specs/fannie-mae/Appendix D-1 SF1_Appraisal/SF1_Appraisal_v1.4.xml"
    assert report.is_file(), f"IT-64R1S4 setup: published report not found: {report}"
    xml = report.read_text(encoding="utf-8-sig")
    target = "customer-it64r1s4-owner-only-" + uuid4().hex
    context = browser.new_context(storage_state=session_state(profile, base))
    page = context.new_page()
    fixture_ready = False
    baseline = None
    connection = sqlite3.connect(store.as_uri() + "?mode=rw", uri=True, isolation_level=None)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        # Do not accept an anonymous denial as evidence of account authorization.
        sign_in(page, profile, base)
        identity_response = context.request.get(base + "/account/context")
        assert identity_response.status == 200, "Setup: the real signed-in test user must have a linked UAD identity."
        identity = identity_response.json()
        assert identity["user_account_id"] == profile["user_account_id"]
        assert any(a["customer_account_id"] == profile["customer_account_id"] and a["can_validate"] for a in identity["accounts"]), (
            "Setup: independently verify this user can validate in the original test account."
        )

        # Real local fixture data; an owner-only membership is denied by IT-44.
        connection.execute("BEGIN IMMEDIATE")
        try:
            assert connection.execute("SELECT 1 FROM entry_users WHERE user_account_id=?", (identity["user_account_id"],)).fetchone()
            connection.execute("INSERT INTO entry_accounts VALUES (?, ?, 1)", (target, "IT-64R1S4 temporary owner-only account"))
            connection.execute("INSERT INTO entry_memberships VALUES (?, ?, 'owner', 1)", (target, identity["user_account_id"]))
            connection.commit()
            fixture_ready = True
        except Exception:
            connection.rollback()
            raise
        actual = context.request.get(base + "/account/context")
        assert actual.status == 200
        selected = next((a for a in actual.json()["accounts"] if a["customer_account_id"] == target), None)
        assert selected and selected["roles"] == ["owner"] and selected["can_validate"] is False, (
            "Setup: the running server must see the same owner-only fixture and deny its validation permission."
        )
        connection.execute("BEGIN")
        baseline = _snapshot(connection)
        connection.commit()

        for variant in ("ordinary-request", "claimed-validator", "conflicting-account-selection"):
            payload = {"customer_account_id": target, "package_name": report.name, "xml_text": xml}
            headers = {"Idempotency-Key": "it64r1s4-" + uuid4().hex}
            if variant == "claimed-validator":
                payload.update({"user_account_id": profile["user_account_id"], "role": "validator", "can_validate": True})
                headers.update({"X-User-Id": profile["user_account_id"], "X-Account-Role": "validator"})
            if variant == "conflicting-account-selection":
                payload["customer_account_id"] = profile["customer_account_id"]
                headers["X-Customer-Account-Id"] = profile["customer_account_id"]
            response = context.request.post(
                base + "/validation-cycles?" + urlencode({"customer_account_id": target}),
                data=payload, headers=headers, max_redirects=0, timeout=30000,
            )
            # APIRequestContext sends a dict as JSON; no appraisal execution should occur.
            assert response.status == 403, (
                f"IT-64R1S4 [{variant}] requires POST /validation-cycles to deny "
                "the verified user's missing permission with HTTP 403 before creating "
                f"resources. Got HTTP {response.status}; missing routes, redirects, "
                "or payload-validation errors do not prove account authorization."
            )
            assert "application/json" in response.headers.get("content-type", "")
            denial = response.json()
            assert isinstance(denial, dict) and isinstance(denial.get("detail"), str)
            assert any(word in denial["detail"].lower() for word in ("permission", "authorized", "membership", "validation access")), (
                "The denial must explain the account authorization requirement."
            )
            assert not ({"validation_cycle_id", "submission_id", "attempt_id", "credit_debit_id", "findings"} & denial.keys())
            connection.execute("BEGIN")
            after = _snapshot(connection)
            connection.commit()
            assert after == baseline, (
                f"IT-64R1S4 [{variant}]: denied request changed cycles, submissions, attempts, "
                "credits, or other protected customer records."
            )
            print(f"{variant}: HTTP 403; protected customer-store state unchanged.")
    finally:
        context.close()
        if fixture_ready:
            connection.execute("BEGIN IMMEDIATE")
            unchanged = baseline is not None and _snapshot(connection) == baseline
            if unchanged:
                connection.execute("DELETE FROM entry_memberships WHERE customer_account_id=?", (target,))
                connection.execute("DELETE FROM entry_accounts WHERE customer_account_id=?", (target,))
                connection.commit()
            else:
                connection.rollback()
                print(f"Fixture preserved for investigation: {target}")
        connection.close()
