"""Executable test for IT-13R1S1 Demo-mode selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


OPERATING_MODE_MODULE = "app.services.operating_modes"
MODE_SERVICE_NAME = "determine_operating_mode"
OPERATING_MODE_NAME = "OperatingMode"


@dataclass
class CountryCallingCodeRecognizerSpy:
    """Return a governed recognized code and record the numeric input."""

    recognized_code: str
    recognition_calls: list[str] = field(default_factory=list)

    def recognize_country_calling_code(
        self,
        internal_phone_number: str,
    ) -> str:
        self.recognition_calls.append(internal_phone_number)
        return self.recognized_code


def _operating_mode_contract() -> tuple[Any, Any]:
    """Load the operating-mode contract expected by IT-13R1S1."""

    try:
        module = import_module(OPERATING_MODE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != OPERATING_MODE_MODULE:
            raise
        pytest.fail(
            "IT-13R1S1 requires app.services.operating_modes before Demo-mode "
            "selection can become green.",
            pytrace=False,
        )

    mode_service = getattr(module, MODE_SERVICE_NAME, None)
    operating_mode = getattr(module, OPERATING_MODE_NAME, None)

    assert callable(mode_service), (
        "IT-13R1S1 requires "
        "app.services.operating_modes.determine_operating_mode"
        "(internal_phone_number, country_calling_code_recognizer)."
    )
    assert operating_mode is not None, (
        "IT-13R1S1 requires app.services.operating_modes.OperatingMode."
    )
    return mode_service, operating_mode


def test_it_13_r1_s1_places_non_country_code_1_user_in_demo_mode() -> None:
    """Select Demo mode without bypassing verification or authorization."""

    determine_operating_mode, operating_mode = _operating_mode_contract()
    internal_phone_number = "44999999999"
    recognizer = CountryCallingCodeRecognizerSpy("44")

    decision = determine_operating_mode(
        internal_phone_number,
        recognizer,
    )

    assert recognizer.recognition_calls == [internal_phone_number]
    assert decision.mode is operating_mode.DEMO
    assert decision.demo_limitations_apply is True
    assert decision.requires_phone_verification is True
    assert decision.requires_account_authorization is True
