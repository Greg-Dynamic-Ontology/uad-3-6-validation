"""Human-user identity services."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol


class HumanUserRegistrationState(StrEnum):
    """State determined solely by normalized phone-number lookup."""

    EXISTING_USER = "existing_user"
    NEW_USER = "new_user"


class HumanUserRepository(Protocol):
    """Phone-number lookup boundary needed for registration-state decisions."""

    def find_by_phone_number(
        self,
        internal_phone_number: str,
    ) -> object | None: ...


class HumanUserActivationRepository(HumanUserRepository, Protocol):
    """Persistence boundary for activating a verified human identity."""

    def create_verified_human_user(
        self,
        internal_phone_number: str,
    ) -> object: ...


class PhoneVerificationGateway(Protocol):
    """Boundary for proving control of a normalized phone number."""

    def proves_control(
        self,
        internal_phone_number: str,
        proof: object,
    ) -> bool: ...


class PhoneControlVerificationError(ValueError):
    """Report that phone control was not proven."""


def determine_registration_state(
    internal_phone_number: str,
    human_user_repository: HumanUserRepository,
) -> HumanUserRegistrationState:
    """Return existing/new state from phone lookup and no other identity data."""

    human_user = human_user_repository.find_by_phone_number(
        internal_phone_number
    )
    if human_user is None:
        return HumanUserRegistrationState.NEW_USER
    return HumanUserRegistrationState.EXISTING_USER


def verify_phone_number_control(
    internal_phone_number: str,
    proof: object,
    verification_gateway: PhoneVerificationGateway,
    human_user_repository: HumanUserActivationRepository,
) -> object:
    """Return one verified identity after phone-control proof succeeds."""

    existing_human_user = human_user_repository.find_by_phone_number(
        internal_phone_number
    )
    if existing_human_user is not None:
        return existing_human_user

    if not verification_gateway.proves_control(
        internal_phone_number,
        proof,
    ):
        raise PhoneControlVerificationError(
            "Control of the phone number could not be verified."
        )

    return human_user_repository.create_verified_human_user(
        internal_phone_number
    )
