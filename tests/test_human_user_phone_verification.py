"""Executable test for IT-11R1S2 phone-control verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from inspect import signature
from typing import Any

import pytest

from app.services.phone_numbers import normalize_phone_number


HUMAN_USER_MODULE = "app.services.human_users"
VERIFICATION_SERVICE_NAME = "verify_phone_number_control"


@dataclass(frozen=True)
class HumanUserRecord:
    """Repository result used to observe activation behavior."""

    identity_id: str
    internal_phone_number: str
    phone_number_verified: bool


@dataclass
class PhoneVerificationGatewaySpy:
    """Accept one proof and record verification activity."""

    accepted_proof: object
    verification_calls: list[tuple[str, object]] = field(default_factory=list)

    def proves_control(
        self,
        internal_phone_number: str,
        proof: object,
    ) -> bool:
        self.verification_calls.append((internal_phone_number, proof))
        return proof is self.accepted_proof


@dataclass
class HumanUserRepositorySpy:
    """Store human identities by canonical internal phone number."""

    records: dict[str, HumanUserRecord] = field(default_factory=dict)
    creation_calls: list[str] = field(default_factory=list)

    def find_by_phone_number(
        self,
        internal_phone_number: str,
    ) -> HumanUserRecord | None:
        return self.records.get(internal_phone_number)

    def create_verified_human_user(
        self,
        internal_phone_number: str,
    ) -> HumanUserRecord:
        self.creation_calls.append(internal_phone_number)
        assert internal_phone_number not in self.records, (
            "The service attempted to create a second identity for one phone number."
        )
        human_user = HumanUserRecord(
            identity_id=f"human-user-{len(self.records) + 1}",
            internal_phone_number=internal_phone_number,
            phone_number_verified=True,
        )
        self.records[internal_phone_number] = human_user
        return human_user


def _verification_contract() -> Any:
    """Load the phone-control service expected by IT-11R1S2."""

    module = import_module(HUMAN_USER_MODULE)
    verification_service = getattr(
        module,
        VERIFICATION_SERVICE_NAME,
        None,
    )
    assert callable(verification_service), (
        "IT-11R1S2 requires "
        "app.services.human_users.verify_phone_number_control"
        "(internal_phone_number, proof, verification_gateway, "
        "human_user_repository)."
    )
    return verification_service


def test_it_11_r1_s2_verifies_phone_control_before_activating_human_user() -> None:
    """Create one verified identity without evaluating account authorization."""

    verify_phone_number_control = _verification_contract()
    parameter_names = signature(verify_phone_number_control).parameters
    assert not any(
        boundary in parameter_name.lower()
        for parameter_name in parameter_names
        for boundary in ("account", "authorization", "membership")
    )

    proof = object()
    verification_gateway = PhoneVerificationGatewaySpy(proof)
    repository = HumanUserRepositorySpy()
    internal_phone_number = normalize_phone_number("+1-999-999-9999")

    activated_human_user = verify_phone_number_control(
        internal_phone_number,
        proof,
        verification_gateway,
        repository,
    )

    assert activated_human_user.internal_phone_number == "19999999999"
    assert activated_human_user.phone_number_verified is True
    assert verification_gateway.verification_calls == [
        (internal_phone_number, proof)
    ]
    assert repository.creation_calls == [internal_phone_number]

    alternate_internal_value = normalize_phone_number("+1 (999) 999-9999")
    assert alternate_internal_value == internal_phone_number
    assert repository.find_by_phone_number(alternate_internal_value) is (
        activated_human_user
    )
    assert len(repository.records) == 1
