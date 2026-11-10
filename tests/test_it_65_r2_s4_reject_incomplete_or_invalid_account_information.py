"""IT-65R2S4: reject invalid account information before persistence.

Service-boundary test; no GraphDB or WorkOS connection is required.
"""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.services.customer_accounts import create_customer_account


class AccountRepository:
    def __init__(self):
        self.added = []

    def add(self, account):
        self.added.append(deepcopy(account))


class AuditHistory:
    def __init__(self):
        self.events = []

    def record(self, **event):
        self.events.append(dict(event))


class AccountIds:
    def __init__(self):
        self.calls = 0

    def new_customer_account_id(self):
        self.calls += 1
        return "urn:uad:test:account:it65-r2-s4"


@pytest.mark.parametrize("account_type", ["solo", "company"])
@pytest.mark.parametrize("invalid_case", ["missing", "blank", "invalid-email", "multiple-errors"])
def test_it_65_r2_s4_reject_incomplete_or_invalid_account_information(account_type, invalid_case):
    owner = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r2-s4",
        workos_user_id="user_it65_r2_s4_owner",
        internal_phone_number="19999999999",
        phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    required = {"display_name", "primary_contact_name", "primary_contact_email"}
    submitted = {
        "display_name": "  Preserve my display name  ",
        "primary_contact_name": "Test Owner",
        "primary_contact_email": "owner@example.test",
        "contact_telephone": "19999999999",
        "postal_address": "  123 Test Street  ",
    }
    if account_type == "company":
        required.add("company_name")
        submitted["company_name"] = "Test Company"
        submitted["company_website"] = "https://company.example.test"

    if invalid_case == "missing":
        for name in required:
            del submitted[name]
        expected_errors = required
    elif invalid_case == "blank":
        for name in required:
            submitted[name] = "   "
        expected_errors = required
    elif invalid_case == "invalid-email":
        submitted["primary_contact_email"] = "not-an-email-address"
        expected_errors = {"primary_contact_email"}
    else:
        submitted["display_name"] = "   "
        submitted["primary_contact_name"] = None
        submitted["primary_contact_email"] = "not-an-email-address"
        expected_errors = {"display_name", "primary_contact_name", "primary_contact_email"}
        if account_type == "company":
            submitted["company_name"] = 123
            expected_errors.add("company_name")

    original = deepcopy(submitted)
    repository = AccountRepository()
    audit = AuditHistory()
    ids = AccountIds()
    failure = None
    try:
        create_customer_account(
            person=owner,
            id_generator=ids,
            account_repository=repository,
            audit_history=audit,
            account_type=account_type,
            account_information=submitted,
        )
    except Exception as error:
        failure = error

    assert failure is not None, "IT-65R2S4 requires invalid account information to be rejected."
    assert not repository.added, "Neither the account nor its owner membership may be saved."
    assert not audit.events, "Rejected input must not record successful account creation or owner assignment."
    assert ids.calls == 0, "Validate submitted information before issuing an account identity."
    assert submitted == original, "Preserve all original values, including whitespace, for correction."

    # Proposed structured error contract for the application/form layer.
    assert getattr(failure, "code", None) == "invalid_account_information", (
        "IT-65R2S4 requires an invalid_account_information failure with "
        f"field_errors and submitted_information; received {type(failure).__name__}."
    )
    field_errors = getattr(failure, "field_errors", None)
    assert isinstance(field_errors, dict)
    assert set(field_errors) == expected_errors, (
        "Identify every invalid required field together, without flagging valid optional fields."
    )
    assert all(isinstance(message, str) and message.strip() for message in field_errors.values())
    preserved = getattr(failure, "submitted_information", None)
    assert preserved == original
    assert getattr(failure, "account_type", None) == account_type
    # The failure must hold a snapshot, not an alias to a subsequently edited form.
    submitted["display_name"] = "User starts correcting the form"
    assert preserved == original
