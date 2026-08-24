"""User operating-mode decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class OperatingMode(StrEnum):
    """Operating modes established by implemented business rules."""

    DEMO = "demo"
    DEVELOPER = "developer"
    STANDARD = "standard"


DESIGNATED_DEVELOPER_PHONE_NUMBER = "19999999977"


@dataclass(frozen=True)
class OperatingModeDecision:
    """Mode selection and the policies it must not bypass."""

    mode: OperatingMode
    demo_limitations_apply: bool
    requires_phone_verification: bool
    requires_account_authorization: bool


class CountryCallingCodeRecognizer(Protocol):
    """Boundary for recognizing a calling code in an internal phone number."""

    def recognize_country_calling_code(
        self,
        internal_phone_number: str,
    ) -> str: ...


class StandardAccountPolicy(Protocol):
    """Boundary for selecting an ordinary country-code-1 user's mode."""

    def select_operating_mode(
        self,
        internal_phone_number: str,
    ) -> OperatingMode: ...


def is_designated_developer_phone_number(
    internal_phone_number: str,
) -> bool:
    """Return whether the number is the one exact Developer-mode number."""

    return internal_phone_number == DESIGNATED_DEVELOPER_PHONE_NUMBER


def determine_operating_mode(
    internal_phone_number: str,
    country_calling_code_recognizer: CountryCallingCodeRecognizer,
    standard_account_policy: StandardAccountPolicy | None = None,
) -> OperatingModeDecision:
    """Apply exact-number precedence before the general calling-code rule."""

    if is_designated_developer_phone_number(internal_phone_number):
        return OperatingModeDecision(
            mode=OperatingMode.DEVELOPER,
            demo_limitations_apply=False,
            requires_phone_verification=True,
            requires_account_authorization=True,
        )

    country_calling_code = (
        country_calling_code_recognizer.recognize_country_calling_code(
            internal_phone_number
        )
    )
    if country_calling_code != "1":
        return OperatingModeDecision(
            mode=OperatingMode.DEMO,
            demo_limitations_apply=True,
            requires_phone_verification=True,
            requires_account_authorization=True,
        )

    if standard_account_policy is None:
        raise ValueError(
            "Standard account policy is required for an ordinary "
            "country-code-1 phone number."
        )

    return OperatingModeDecision(
        mode=standard_account_policy.select_operating_mode(
            internal_phone_number
        ),
        demo_limitations_apply=False,
        requires_phone_verification=True,
        requires_account_authorization=True,
    )
