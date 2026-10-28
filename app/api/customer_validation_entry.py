"""Verified browser entry to account-owned validation; no cycle creation."""

from html import escape
import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.adapters.customer_validation_store import CustomerValidationStore
from app.services.account_authorization import (
    AuthorizationResult, CustomerAccountActivity, authorize_customer_activity,
)
from app.services.customer_accounts import CustomerAccountMembership, CustomerAccountRole
from app.services.operating_modes import OperatingMode, determine_operating_mode


router = APIRouter()


class _CallingCodePolicy:
    def recognize_country_calling_code(self, internal_phone_number: str) -> str:
        return "1" if internal_phone_number.startswith("1") else "other"


class _StandardModePolicy:
    def select_operating_mode(self, internal_phone_number: str) -> OperatingMode:
        return OperatingMode.STANDARD


def _verified_identity(request: Request):
    from app import main

    if not request.cookies.get(main.SESSION_COOKIE_NAME):
        return None
    required = ("WORKOS_API_KEY", "WORKOS_CLIENT_ID", "WORKOS_COOKIE_PASSWORD")
    if any(not os.environ.get(name) for name in required):
        raise HTTPException(503, "Hosted sign-in is not configured in the running server.")
    workos = main.WorkOSClient(
        api_key=os.environ["WORKOS_API_KEY"], client_id=os.environ["WORKOS_CLIENT_ID"],
    )
    return main._authenticated_workos_user(request, workos)


def _account_context(request: Request) -> dict:
    identity = _verified_identity(request)
    if identity is None:
        raise HTTPException(401, "Sign in to use customer-account validation.")
    store = CustomerValidationStore()
    user = store.user_for_identity(str(identity["id"]))
    if user is None:
        raise HTTPException(403, "The authenticated identity has no registered customer user link.")
    if not user["phone_verified"]:
        raise HTTPException(403, "A verified phone number is required for account validation.")
    mode = determine_operating_mode(
        user["internal_phone_number"], _CallingCodePolicy(), _StandardModePolicy(),
    )
    accounts = store.accounts_for_user(user["user_account_id"])
    for account in accounts:
        account["can_validate"] = not mode.demo_limitations_apply and any(
            authorize_customer_activity(
                CustomerAccountMembership(
                    human_user_id=user["user_account_id"],
                    role=CustomerAccountRole(role), active=True,
                    customer_account_id=account["customer_account_id"],
                ),
                account["customer_account_id"],
                CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
            ).result is AuthorizationResult.ALLOWED
            for role in account["roles"]
        )
    return {
        "user_account_id": user["user_account_id"],
        "display_name": user["display_name"],
        "operating_mode": mode.mode.value,
        "accounts": accounts,
    }


def _selected_account(context: dict, customer_account_id: str) -> dict:
    for account in context["accounts"]:
        if account["customer_account_id"] == customer_account_id and account["can_validate"]:
            return account
    raise HTTPException(403, "An active validation membership in this customer account is required.")


@router.get("/login")
def start_customer_sign_in():
    from app import main

    required = ("WORKOS_API_KEY", "WORKOS_CLIENT_ID", "WORKOS_COOKIE_PASSWORD", "WORKOS_REDIRECT_URI")
    if any(not os.environ.get(name) for name in required):
        raise HTTPException(503, "Hosted sign-in is not configured in the running server.")
    workos = main.WorkOSClient(
        api_key=os.environ["WORKOS_API_KEY"], client_id=os.environ["WORKOS_CLIENT_ID"],
    )
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit", redirect_uri=os.environ["WORKOS_REDIRECT_URI"],
    )
    return RedirectResponse(authorization_url, status_code=303)


@router.get("/account/context")
def get_customer_account_context(request: Request):
    return _account_context(request)


@router.get("/validation-cycles")
def list_account_validation_cycles(request: Request, customer_account_id: str):
    context = _account_context(request)
    _selected_account(context, customer_account_id)
    return {
        "customer_account_id": customer_account_id,
        "cycles": CustomerValidationStore().cycles_for_account(customer_account_id),
    }


@router.get("/validation/", response_class=HTMLResponse)
def account_validation_page(request: Request, customer_account_id: str | None = None):
    from app import main

    # The existing anonymous Demo page remains available at its original URL.
    if not customer_account_id:
        return FileResponse(main.SITE_DIRECTORY / "validation" / "index.html")
    context = _account_context(request)
    account = _selected_account(context, customer_account_id)
    query = urlencode({"customer_account_id": customer_account_id})
    return HTMLResponse(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Account report validation</title><link rel="stylesheet" href="/assets/css/site.css"></head>
<body><main class="content-section">
<h1>Account report validation</h1>
<p id="authenticated-user" data-user-account-id="{escape(context['user_account_id'])}">
Signed in as {escape(context['display_name'])}</p>
<p id="selected-customer-account" data-customer-account-id="{escape(customer_account_id)}">
Customer account: {escape(account['label'])}</p>
<p id="operating-mode" data-operating-mode="{escape(context['operating_mode'])}">
{escape(context['operating_mode'].title())} mode</p>
<button type="button" id="new-cycle-action" aria-controls="new-cycle-preparation" aria-expanded="false">
New validation cycle</button>
<section id="new-cycle-preparation" hidden><h2>Prepare a new validation cycle</h2>
<p>Choose the report you intend to validate. No cycle is created by opening this page.</p>
<label for="new-report">Appraisal XML report</label><input id="new-report" type="file" accept=".xml">
<p role="status">Report submission for a new cycle is not yet available.</p></section>
<p><a href="/validation-cycles?{escape(query)}">View recorded validation cycles</a></p>
<p><a href="/">Home</a></p>
</main><script>
document.getElementById('new-cycle-action').addEventListener('click', (event) => {{
  document.getElementById('new-cycle-preparation').hidden = false;
  event.currentTarget.setAttribute('aria-expanded', 'true');
}});
</script></body></html>''')
