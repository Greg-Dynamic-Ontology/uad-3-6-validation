"""Customer-account creation and identity-preserving information updates."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from collections.abc import Mapping
from enum import StrEnum
from copy import deepcopy
from email.headerregistry import Address
from email.errors import HeaderParseError
from typing import Protocol
from uuid import uuid4
from hashlib import sha256
import json


class CustomerAccountRole(StrEnum):
    """Customer-account roles established by implemented business rules."""

    OWNER = "owner"
    BILLING_ADMINISTRATOR = "billing administrator"
    VALIDATOR = "validator"
    REVIEWER = "reviewer"


@dataclass(frozen=True)
class CustomerAccountMembership:
    """A human user's active role within one customer account."""

    human_user_id: str
    role: CustomerAccountRole
    active: bool
    customer_account_id: str | None = None


@dataclass(frozen=True)
class CustomerAccount:
    """Ownership and billing boundary with its initial membership."""

    customer_account_id: str
    is_ownership_boundary: bool
    is_billing_boundary: bool
    memberships: tuple[CustomerAccountMembership, ...]
    display_name: str = ""
    account_type: str = "solo"
    status: str = "active"
    primary_contact_name: str = ""
    primary_contact_email: str = ""
    company_name: str = ""
    contact_telephone: str = ""
    postal_address: str = ""
    company_website: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    creation_request_id: str = ""
    creation_request_actor_id: str = ""
    creation_request_fingerprint: str = ""


class CustomerAccountApplicant(Protocol):
    """Verified, eligible human user creating an account."""

    human_user_id: str
    internal_phone_number: str
    phone_number_verified: bool
    eligible_to_create_customer_account: bool


class CustomerAccountIdGenerator(Protocol):
    """Boundary for issuing unique customer-account identifiers."""

    def new_customer_account_id(self) -> str: ...


class UniqueCustomerAccountIdGenerator:
    """Issue account IDs independently of UAD and authentication identities."""

    def new_customer_account_id(self) -> str:
        return f"urn:uad:customer-account:{uuid4()}"


class CustomerAccountUpdateRepository(Protocol):
    """Persistence boundary for saving an existing account aggregate."""

    def save(self, customer_account: CustomerAccount) -> None: ...

class CustomerAccountRepository(Protocol):
    """Persistence boundary for customer-account aggregates."""

    def add(self, customer_account: CustomerAccount) -> None: ...


class AccountAuditHistory(Protocol):
    """Audit boundary for material customer-account events."""

    def record(self, **event: str) -> None: ...


class AccountCreationRequestConflict(ValueError):
    """A completed creation request ID was reused with different information."""

    code = "account_creation_request_conflict"

class InvalidAccountInformationError(ValueError):
    """Field diagnostics and the unchanged submission for form correction."""

    code = "invalid_account_information"

    def __init__(self, *, account_type, field_errors, submitted_information):
        self.account_type = account_type
        self.field_errors = dict(field_errors)
        self.submitted_information = deepcopy(submitted_information)
        super().__init__(
            "Correct the following account-information fields: "
            + ", ".join(sorted(self.field_errors))
        )


def _valid_contact_email(value: str) -> bool:
    """Check address syntax without claiming mailbox ownership or delivery."""
    if "\r" in value or "\n" in value:
        return False
    try:
        address = Address(addr_spec=value)
    except (ValueError, HeaderParseError):
        return False
    return bool(address.username and address.domain)


def _validated_account_information(account_type, submitted) -> dict[str, str]:
    errors = {}
    valid_type = isinstance(account_type, str) and account_type in {"solo", "company"}
    if not valid_type:
        errors["account_type"] = "Choose solo or company."
    if not isinstance(submitted, Mapping):
        errors["account_information"] = "Supply the account information."
        raise InvalidAccountInformationError(
            account_type=account_type, field_errors=errors,
            submitted_information=submitted,
        )

    required = {"display_name", "primary_contact_name", "primary_contact_email"}
    if account_type == "company":
        required.add("company_name")
    allowed = required | {"contact_telephone", "postal_address"}
    if account_type == "company":
        allowed.add("company_website")
    for name in submitted:
        if name not in allowed:
            errors[str(name)] = "This field is not supported for the selected account type."

    normalized = {}
    for name in sorted(allowed):
        value = submitted.get(name, "")
        if not isinstance(value, str):
            errors[name] = "Enter a text value."
            continue
        normalized[name] = value.strip()
        if name in required and not normalized[name]:
            errors[name] = "This field is required."
    email = normalized.get("primary_contact_email", "")
    if email and not _valid_contact_email(email):
        errors["primary_contact_email"] = "Enter a valid email address, such as name@example.com."
    if errors:
        raise InvalidAccountInformationError(
            account_type=account_type, field_errors=errors,
            submitted_information=dict(submitted),
        )
    return normalized

def create_customer_account(
    person: CustomerAccountApplicant,
    id_generator: CustomerAccountIdGenerator,
    account_repository: CustomerAccountRepository,
    audit_history: AccountAuditHistory,
    *,
    account_type: str | None = None,
    account_information: Mapping[str, object] | None = None,
    request_id: str | None = None,
) -> CustomerAccount:
    """Create an active account and its first owner as one aggregate.

    Explicit solo/company submissions require the corresponding information.
    The original four-argument service contract remains available for existing
    callers; new account-creation flows should supply both keyword arguments.
    """
    if not person.eligible_to_create_customer_account or not person.phone_number_verified:
        raise PermissionError("A verified, eligible user is required to create an account.")
    if not isinstance(person.human_user_id, str) or not person.human_user_id.strip():
        raise ValueError("An identified UAD user is required.")

    information = {}
    if account_type is not None or account_information is not None:
        information = _validated_account_information(account_type, account_information)
    else:
        # Preserve the original service contract for established callers.
        account_type = "solo"

    request_fingerprint = ""
    if request_id is not None:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("A supplied account-creation request ID must be nonempty text.")
        request_fingerprint = sha256(json.dumps(
            {"account_type": account_type, "account_information": information},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        lookup = getattr(account_repository, "find_by_creation_request", None)
        if not callable(lookup):
            raise TypeError("The repository must support durable account-creation request lookup.")
        existing = lookup(actor_id=person.human_user_id, request_id=request_id)
        if existing is not None:
            if (
                existing.creation_request_actor_id != person.human_user_id
                or existing.creation_request_id != request_id
                or existing.creation_request_fingerprint != request_fingerprint
            ):
                raise AccountCreationRequestConflict(
                    "This request ID was already used for different account information."
                )
            return existing

    customer_account_id = id_generator.new_customer_account_id()
    if not isinstance(customer_account_id, str) or not customer_account_id.strip():
        raise ValueError("The account ID generator must return a nonempty identifier.")
    if customer_account_id in {
        person.human_user_id, getattr(person, "workos_user_id", None),
    }:
        raise ValueError("The customer-account ID must be distinct from the owner's identities.")
    owner_membership = CustomerAccountMembership(
        human_user_id=person.human_user_id,
        role=CustomerAccountRole.OWNER,
        active=True,
        customer_account_id=customer_account_id,
    )
    customer_account = CustomerAccount(
        customer_account_id=customer_account_id,
        is_ownership_boundary=True,
        is_billing_boundary=True,
        memberships=(owner_membership,),
        account_type=account_type,
        status="active",
        creation_request_id=request_id or "",
        creation_request_actor_id=person.human_user_id if request_id is not None else "",
        creation_request_fingerprint=request_fingerprint,
        **information,
    )
    # The repository persists the account and membership together. In the
    # GraphDB adapter this aggregate also carries the owner for attribution.
    account_repository.add(customer_account)
    audit_history.record(
        event_type="customer_account_created",
        customer_account_id=customer_account_id,
        actor_id=person.human_user_id,
    )
    audit_history.record(
        event_type="owner_assigned",
        customer_account_id=customer_account_id,
        actor_id=person.human_user_id,
        subject_id=person.human_user_id,
    )
    return customer_account

def update_customer_account_information(
    *,
    customer_account: CustomerAccount,
    display_name: str | None = None,
    actor_id: str,
    account_repository: CustomerAccountUpdateRepository,
    audit_history: AccountAuditHistory,
    account_information: Mapping[str, object] | None = None,
) -> CustomerAccount:
    """Update editable information while preserving identity and ownership.

    Supply a trusted persisted aggregate and the authenticated UAD actor.
    Mapping submissions are partial updates: omitted fields retain their values.
    The original display-name-only call remains supported.
    """
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("An identified acting UAD user is required.")
    authorized = any(
        membership.active
        and membership.role == CustomerAccountRole.OWNER
        and membership.human_user_id == actor_id
        and membership.customer_account_id == customer_account.customer_account_id
        for membership in customer_account.memberships
    )
    if not authorized or customer_account.status != "active":
        raise PermissionError("An active owner of an active account must update its information.")

    if account_information is None:
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("Account display name must contain non-whitespace text.")
        information = {"display_name": display_name.strip()}
    else:
        if display_name is not None:
            raise ValueError("Supply display_name or account_information, not both.")
        if not isinstance(account_information, Mapping):
            raise InvalidAccountInformationError(
                account_type=customer_account.account_type,
                field_errors={"account_information": "Supply the account information."},
                submitted_information=account_information,
            )
        fields = {
            "display_name", "primary_contact_name", "primary_contact_email",
            "contact_telephone", "postal_address",
        }
        if customer_account.account_type == "company":
            fields.update({"company_name", "company_website"})
        merged = {name: getattr(customer_account, name) for name in fields}
        merged.update(account_information)
        try:
            validated = _validated_account_information(customer_account.account_type, merged)
        except InvalidAccountInformationError as error:
            raise InvalidAccountInformationError(
                account_type=customer_account.account_type,
                field_errors=error.field_errors,
                submitted_information=dict(account_information),
            ) from error
        information = {name: validated[name] for name in account_information}

    updated = replace(customer_account, **information)
    # GraphDB persists the field changes and actor/time attribution together.
    # Retain the original repository protocol for existing in-memory callers.
    save_information = getattr(account_repository, "save_information", None)
    if callable(save_information):
        # Carry the state originally read by the administrator. Comparing only
        # a fresh adapter read cannot detect an already-obsolete submission.
        save_information(
            updated, actor_id=actor_id, expected_account=customer_account,
        )
    else:
        account_repository.save(updated)
    audit_history.record(
        event_type="customer_account_information_updated",
        customer_account_id=customer_account.customer_account_id,
        actor_id=actor_id,
    )
    return updated

@dataclass(frozen=True)
class CustomerAccountSummary:
    """Account-list information for the authenticated user's own memberships."""

    customer_account_id: str
    display_name: str
    account_type: str
    status: str
    role: str


class CustomerAccountListingRepository(Protocol):
    def list_for_user(self, human_user_id: str) -> tuple[CustomerAccount, ...]: ...


def list_customer_accounts(
    *, human_user_id: str, account_repository: CustomerAccountListingRepository,
) -> tuple[CustomerAccountSummary, ...]:
    """List accounts accessible through this user's active memberships.

    The caller supplies the authenticated stable UAD user ID. Summary records
    contain no other members' identity or contact information. Where a user has
    multiple active roles, the display text names each role once.
    """
    if not isinstance(human_user_id, str) or not human_user_id.strip():
        raise PermissionError("An authenticated UAD user is required to list accounts.")
    summaries = {}
    for account in account_repository.list_for_user(human_user_id):
        roles = {
            str(membership.role)
            for membership in account.memberships
            if membership.active
            and membership.human_user_id == human_user_id
            and membership.customer_account_id == account.customer_account_id
        }
        # Enforce the account boundary here as well as in the storage adapter.
        if not roles:
            continue
        summaries[account.customer_account_id] = CustomerAccountSummary(
            customer_account_id=account.customer_account_id,
            display_name=account.display_name,
            account_type=account.account_type,
            status=account.status,
            role=", ".join(sorted(roles)),
        )
    return tuple(sorted(
        summaries.values(),
        key=lambda summary: (summary.display_name.casefold(), summary.customer_account_id),
    ))

@dataclass(frozen=True)
class SelectedCustomerAccountView:
    """Stored account details bound to the viewing user's account context."""

    selected_customer_account_id: str
    account: CustomerAccount
    membership: CustomerAccountMembership


def view_customer_account(
    *,
    human_user_id: str,
    customer_account_id: str,
    account_repository: CustomerAccountListingRepository,
) -> SelectedCustomerAccountView:
    """Return a selected account only through an active membership.

    Use the authenticated stable UAD user ID supplied by the application.
    The repository supplies persisted accounts and memberships from one read.
    Selection is explicit per call; no process-wide selected account is stored.
    """
    denied = "The selected customer account is not available to this user."
    if not isinstance(human_user_id, str) or not human_user_id.strip():
        raise PermissionError(denied)
    if not isinstance(customer_account_id, str) or not customer_account_id.strip():
        raise PermissionError(denied)
    for account in account_repository.list_for_user(human_user_id):
        if account.customer_account_id != customer_account_id:
            continue
        membership = next((
            candidate for candidate in account.memberships
            if candidate.active
            and candidate.human_user_id == human_user_id
            and candidate.customer_account_id == customer_account_id
        ), None)
        if membership is None:
            continue
        return SelectedCustomerAccountView(
            selected_customer_account_id=account.customer_account_id,
            account=account,
            membership=membership,
        )
    # Do not distinguish a nonexistent account from an inaccessible one.
    raise PermissionError(denied)
