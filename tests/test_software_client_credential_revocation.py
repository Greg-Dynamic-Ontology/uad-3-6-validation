"""Executable test for IT-20R1S2 software-client credential revocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)
from app.services.software_clients import (
    SoftwareClient,
    SoftwareClientScope,
    authorize_software_client,
)


SOFTWARE_CLIENT_MODULE = "app.services.software_clients"


@dataclass(frozen=True)
class SoftwareClientCredential:
    credential_id: str
    software_client_id: str
    customer_account_id: str
    active: bool


@dataclass
class SoftwareClientCredentialRepositorySpy:
    saved_credentials: list[SoftwareClientCredential] = field(
        default_factory=list
    )

    def save(self, credential: SoftwareClientCredential) -> None:
        self.saved_credentials.append(credential)


@dataclass(frozen=True)
class AccountRecord:
    record_id: str
    customer_account_id: str
    value: str


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, **event: object) -> None:
        self.events.append(event)


def _credential_revocation_contract() -> Any:
    """Load the credential-revocation contract expected by IT-20R1S2."""

    module = import_module(SOFTWARE_CLIENT_MODULE)
    revoke_credentials = getattr(
        module,
        "revoke_software_client_credentials",
        None,
    )
    assert callable(revoke_credentials), (
        "IT-20R1S2 requires revoke_software_client_credentials("
        "owner_membership, software_client, credential, "
        "credential_repository, audit_history)."
    )
    return revoke_credentials


def test_it_20_r1_s2_revokes_software_client_credentials_only() -> None:
    """Disable authentication while preserving identity and account records."""

    revoke_credentials = _credential_revocation_contract()
    customer_account_id = "customer-account-1"
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    software_client = SoftwareClient(
        software_client_id="software-client-1",
        customer_account_id=customer_account_id,
        granted_scopes=frozenset({SoftwareClientScope.SUBMIT_REPORTS}),
        active=True,
    )
    credential = SoftwareClientCredential(
        credential_id="software-credential-1",
        software_client_id=software_client.software_client_id,
        customer_account_id=customer_account_id,
        active=True,
    )
    account_records = (
        AccountRecord("report-1", customer_account_id, "retained report"),
        AccountRecord("audit-1", customer_account_id, "retained history"),
    )
    original_account_records = account_records
    credentials = SoftwareClientCredentialRepositorySpy()
    audit_history = AccountAuditHistorySpy()

    assert authorize_software_client(
        credential,
        software_client,
        customer_account_id,
        SoftwareClientScope.SUBMIT_REPORTS,
    ) is True

    revoked_credential = revoke_credentials(
        owner,
        software_client,
        credential,
        credentials,
        audit_history,
    )

    assert revoked_credential.active is False
    assert credentials.saved_credentials == [revoked_credential]
    assert authorize_software_client(
        revoked_credential,
        software_client,
        customer_account_id,
        SoftwareClientScope.SUBMIT_REPORTS,
    ) is False
    assert software_client.active is True
    assert account_records == original_account_records
    assert audit_history.events == [
        {
            "event_type": "software_client_credentials_revoked",
            "customer_account_id": customer_account_id,
            "actor_id": owner.human_user_id,
            "subject_id": software_client.software_client_id,
            "credential_id": credential.credential_id,
        }
    ]
