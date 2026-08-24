"""Executable test for IT-13R1S3 standard-policy mode selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any


OPERATING_MODE_MODULE = "app.services.operating_modes"


@dataclass
class CountryCallingCodeRecognizerSpy:
    """Recognize country calling code 1 and record the internal value."""

    recognition_calls: list[str] = field(default_factory=list)

    def recognize_country_calling_code(
        self,
        internal_phone_number: str,
    ) -> str:
        self.recognition_calls.append(internal_phone_number)
        return "1"


@dataclass
class StandardAccountPolicySpy:
    """Select the configured standard mode and record delegation."""

    selected_mode: object
    selection_calls: list[str] = field(default_factory=list)

    def select_operating_mode(self, internal_phone_number: str) -> object:
        self.selection_calls.append(internal_phone_number)
        return self.selected_mode


def _standard_mode_contract() -> tuple[Any, Any, Any]:
    """Load the standard-policy contract expected by IT-13R1S3."""

    module = import_module(OPERATING_MODE_MODULE)
    determine_operating_mode = getattr(
        module,
        "determine_operating_mode",
        None,
    )
    operating_mode = getattr(module, "OperatingMode", None)
    is_designated_developer_phone_number = getattr(
        module,
        "is_designated_developer_phone_number",
        None,
    )

    assert callable(determine_operating_mode)
    assert operating_mode is not None and hasattr(
        operating_mode,
        "STANDARD",
    ), "IT-13R1S3 requires OperatingMode.STANDARD."
    assert callable(is_designated_developer_phone_number)
    return (
        determine_operating_mode,
        operating_mode,
        is_designated_developer_phone_number,
    )


def test_it_13_r1_s3_delegates_other_country_code_1_user_to_standard_policy() -> None:
    """Do not force an ordinary country-code-1 user into Demo or Developer."""

    (
        determine_operating_mode,
        operating_mode,
        is_designated_developer_phone_number,
    ) = _standard_mode_contract()
    internal_phone_number = "19999999976"
    recognizer = CountryCallingCodeRecognizerSpy()
    standard_account_policy = StandardAccountPolicySpy(
        operating_mode.STANDARD
    )

    assert is_designated_developer_phone_number(internal_phone_number) is False

    decision = determine_operating_mode(
        internal_phone_number,
        recognizer,
        standard_account_policy,
    )

    assert recognizer.recognition_calls == [internal_phone_number]
    assert standard_account_policy.selection_calls == [internal_phone_number]
    assert decision.mode is operating_mode.STANDARD
    assert decision.mode is not operating_mode.DEMO
    assert decision.mode is not operating_mode.DEVELOPER
    assert decision.demo_limitations_apply is False
    assert decision.requires_phone_verification is True
    assert decision.requires_account_authorization is True
