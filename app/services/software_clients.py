"""Account-bound software-client identities, credentials, and scopes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


class SoftwareClientScope(StrEnum):
    """Explicit permissions that may be granted to a software client."""

    SUBMIT_REPORTS = "submit reports"
    MANAGE_BILLING = "manage billing"


@dataclass(frozen=True)
class SoftwareClient:
    """A non-human identity acting for exactly one customer account."""

    software_client_id: str
    customer_account_id: str
    granted_scopes: frozenset[SoftwareClientScope]
    active: bool


class IssuedSoftwareClientCredential(Protocol):
    credential_id: str
    software_client_id: str
    customer_account_id: str
    active: bool


@dataclass(frozen=True)
class SoftwareClientRegistration:
    """A created identity and its separately issued credential."""

    software_client: SoftwareClient
    credential: IssuedSoftwareClientCredential


class SoftwareClientIdGenerator(Protocol):
    def new_software_client_id(self) -> str: ...


class SoftwareClientCredentialIssuer(Protocol):
    def issue_software_client_credential(
        self,
        software_client_id: str,
        customer_account_id: str,
    ) -> IssuedSoftwareClientCredential: ...


class SoftwareClientRepository(Protocol):
    def add(self, software_client: SoftwareClient) -> None: ...


class SoftwareClientCredentialRepository(Protocol):
    def save(
        self,
        credential: IssuedSoftwareClientCredential,
    ) -> None: ...


class AccountAuditHistory(Protocol):
    def record(self, **event: object) -> None: ...


def create_software_client(
    owner_membership: CustomerAccountMembership,
    granted_scopes: set[SoftwareClientScope],
    id_generator: SoftwareClientIdGenerator,
    credential_issuer: SoftwareClientCredentialIssuer,
    repository: SoftwareClientRepository,
    audit_history: AccountAuditHistory,
) -> SoftwareClientRegistration:
    """Create one scoped software identity with non-human credentials."""

    if (
        not owner_membership.active
        or owner_membership.role is not CustomerAccountRole.OWNER
        or owner_membership.customer_account_id is None
    ):
        raise PermissionError(
            "An active customer-account owner must create software clients."
        )
    if not granted_scopes:
        raise ValueError("A software client requires an explicit scope.")

    software_client = SoftwareClient(
        software_client_id=id_generator.new_software_client_id(),
        customer_account_id=owner_membership.customer_account_id,
        granted_scopes=frozenset(granted_scopes),
        active=True,
    )
    credential = credential_issuer.issue_software_client_credential(
        software_client.software_client_id,
        software_client.customer_account_id,
    )
    repository.add(software_client)
    audit_history.record(
        event_type="software_client_created",
        customer_account_id=software_client.customer_account_id,
        actor_id=owner_membership.human_user_id,
        subject_id=software_client.software_client_id,
    )
    return SoftwareClientRegistration(
        software_client=software_client,
        credential=credential,
    )


def authorize_software_client(
    credential: IssuedSoftwareClientCredential,
    software_client: SoftwareClient,
    customer_account_id: str,
    required_scope: SoftwareClientScope,
) -> bool:
    """Authorize only a bound credential, account, and granted scope."""

    return (
        software_client.active
        and getattr(credential, "active", True)
        and software_client.customer_account_id == customer_account_id
        and credential.software_client_id
        == software_client.software_client_id
        and credential.customer_account_id == customer_account_id
        and required_scope in software_client.granted_scopes
    )


def revoke_software_client_credentials(
    owner_membership: CustomerAccountMembership,
    software_client: SoftwareClient,
    credential: IssuedSoftwareClientCredential,
    credential_repository: SoftwareClientCredentialRepository,
    audit_history: AccountAuditHistory,
) -> IssuedSoftwareClientCredential:
    """Revoke one bound credential without changing client or account data."""

    owner_is_authorized = (
        owner_membership.active
        and owner_membership.role is CustomerAccountRole.OWNER
        and owner_membership.customer_account_id
        == software_client.customer_account_id
    )
    credential_is_bound = (
        credential.software_client_id == software_client.software_client_id
        and credential.customer_account_id
        == software_client.customer_account_id
    )
    if not owner_is_authorized or not credential_is_bound:
        raise PermissionError(
            "An active owner may revoke only credentials in the same account."
        )

    revoked_credential = replace(credential, active=False)
    credential_repository.save(revoked_credential)
    audit_history.record(
        event_type="software_client_credentials_revoked",
        customer_account_id=software_client.customer_account_id,
        actor_id=owner_membership.human_user_id,
        subject_id=software_client.software_client_id,
        credential_id=credential.credential_id,
    )
    return revoked_credential
