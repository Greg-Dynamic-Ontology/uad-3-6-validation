"""Executable tests for IT-13R1S2 Developer-mode selection."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest


OPERATING_MODE_MODULE = "app.services.operating_modes"


class CountryCallingCodeMustNotBeUsed:
    """Fail if the general country-code rule precedes the exact-number rule."""

    def recognize_country_calling_code(
        self,
        internal_phone_number: str,
    ) -> str:
        pytest.fail(
            "The exact developer-number rule must precede country-code recognition."
        )


def _developer_mode_contract() -> tuple[Any, Any, Any]:
    """Load the Developer-mode contract expected by IT-13R1S2."""

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
        "DEVELOPER",
    ), "IT-13R1S2 requires OperatingMode.DEVELOPER."
    assert callable(is_designated_developer_phone_number), (
        "IT-13R1S2 requires an exact "
        "is_designated_developer_phone_number(internal_phone_number) rule."
    )
    return (
        determine_operating_mode,
        operating_mode,
        is_designated_developer_phone_number,
    )


def test_it_13_r1_s2_places_designated_phone_number_in_developer_mode() -> None:
    """Apply the exact developer rule before the general country-code rule."""

    (
        determine_operating_mode,
        operating_mode,
        is_designated_developer_phone_number,
    ) = _developer_mode_contract()
    internal_phone_number = "19999999977"

    assert is_designated_developer_phone_number(internal_phone_number) is True

    decision = determine_operating_mode(
        internal_phone_number,
        CountryCallingCodeMustNotBeUsed(),
    )

    assert decision.mode is operating_mode.DEVELOPER
    assert decision.demo_limitations_apply is False
    assert decision.requires_phone_verification is True
    assert decision.requires_account_authorization is True


@pytest.mark.parametrize(
    "other_internal_phone_number",
    [
        "19999999976",
        "44999999999",
    ],
    ids=["adjacent-country-code-1-number", "non-1-country-code-number"],
)
def test_it_13_r1_s2_does_not_designate_any_other_phone_number(
    other_internal_phone_number: str,
) -> None:
    """Keep Developer-mode designation exclusive to the exact number."""

    _, _, is_designated_developer_phone_number = _developer_mode_contract()

    assert (
        is_designated_developer_phone_number(other_internal_phone_number)
        is False
    )
