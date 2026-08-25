"""Executable test for IT-20R1S1 software-client creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any

import pytest

from app.services.account_audit import (
    MaterialActionOutcome,
    record_material_account_action,
)
from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


SOFTWARE_CLIENT_MODULE = "app.services.software_clients"


@dataclass
class SoftwareClientIdGeneratorStub:
    def new_software_client_id(self) -> str:
        return "software-client-1"


@dataclass(frozen=True)
class IssuedSoftwareClientCredential:
    credential_id: str
    software_client_id: str
    customer_account_id: str
    secret: str


@dataclass
class SoftwareClientCredentialIssuerSpy:
    calls: list[dict[str, str]] = field(default_factory=list)

    def issue_software_client_credential(
        self,
        software_client_id: str,
        customer_account_id: str,
    ) -> IssuedSoftwareClientCredential:
        self.calls.append(
            {
                "software_client_id": software_client_id,
                "customer_account_id": customer_account_id,
            }
        )
        return IssuedSoftwareClientCredential(
            credential_id="software-credential-1",
            software_client_id=software_client_id,
            customer_account_id=customer_account_id,
            secret="software-client-secret",
        )


@dataclass
class SoftwareClientRepositorySpy:
    software_clients: list[object] = field(default_factory=list)

    def add(self, software_client: object) -> None:
        self.software_clients.append(software_client)


@dataclass
class EventHistorySpy:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, **event: object) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class ClockStub:
    def now(self) -> datetime:
        return datetime(2026, 8, 25, 16, 0, tzinfo=timezone.utc)


@dataclass
class MaterialActionAuditRepositorySpy:
    records: list[object] = field(default_factory=list)

    def add(self, record: object) -> None:
        self.records.append(record)


def _software_client_contract() -> tuple[Any, Any, Any]:
    """Load the software-client contract expected by IT-20R1S1."""

    try:
        module = import_module(SOFTWARE_CLIENT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != SOFTWARE_CLIENT_MODULE:
            raise
        pytest.fail(
            "IT-20R1S1 requires app.services.software_clients before "
            "software-client creation can become green.",
            pytrace=False,
        )

    create_client = getattr(module, "create_software_client", None)
    authorize_client = getattr(module, "authorize_software_client", None)
    scope = getattr(module, "SoftwareClientScope", None)
    assert callable(create_client), (
        "IT-20R1S1 requires create_software_client(owner_membership, "
        "granted_scopes, id_generator, credential_issuer, repository, "
        "audit_history)."
    )
    assert callable(authorize_client), (
        "IT-20R1S1 requires authorize_software_client(credential, "
        "software_client, customer_account_id, required_scope)."
    )
    assert scope is not None, "IT-20R1S1 requires SoftwareClientScope."
    assert hasattr(scope, "SUBMIT_REPORTS")
    assert hasattr(scope, "MANAGE_BILLING")
    return create_client, authorize_client, scope


def test_it_20_r1_s1_creates_separate_scoped_software_client() -> None:
    """Create, scope, isolate, and attribute a non-human client identity."""

    create_client, authorize_client, scope = _software_client_contract()
    customer_account_id = "customer-account-1"
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    human_login_credential_id = "human-login-credential-1"
    credential_issuer = SoftwareClientCredentialIssuerSpy()
    repository = SoftwareClientRepositorySpy()
    audit_history = EventHistorySpy()

    registration = create_client(
        owner,
        {scope.SUBMIT_REPORTS},
        SoftwareClientIdGeneratorStub(),
        credential_issuer,
        repository,
        audit_history,
    )

    software_client = registration.software_client
    credential = registration.credential
    assert software_client.software_client_id == "software-client-1"
    assert software_client.software_client_id != owner.human_user_id
    assert software_client.customer_account_id == customer_account_id
    assert software_client.active is True
    assert software_client.granted_scopes == frozenset({scope.SUBMIT_REPORTS})
    assert credential.credential_id != human_login_credential_id
    assert credential.software_client_id == software_client.software_client_id
    assert not hasattr(credential, "human_user_id")
    assert repository.software_clients == [software_client]

    assert authorize_client(
        credential,
        software_client,
        customer_account_id,
        scope.SUBMIT_REPORTS,
    ) is True
    assert authorize_client(
        credential,
        software_client,
        customer_account_id,
        scope.MANAGE_BILLING,
    ) is False
    assert authorize_client(
        credential,
        software_client,
        "customer-account-2",
        scope.SUBMIT_REPORTS,
    ) is False

    action_audit = MaterialActionAuditRepositorySpy()
    action_record = record_material_account_action(
        customer_account_id,
        software_client.software_client_id,
        "submit report for validation",
        MaterialActionOutcome.ACCEPTED,
        ClockStub(),
        action_audit,
        affected_resource_id="report-1",
    )
    assert action_record.actor_id == software_client.software_client_id
