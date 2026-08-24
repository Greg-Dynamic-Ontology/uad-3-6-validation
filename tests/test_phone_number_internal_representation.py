"""Executable test for IT-10R1S4 internal phone-number representation."""

from __future__ import annotations

import pytest

from app.services.phone_numbers import (
    format_phone_number_for_form,
    normalize_phone_number,
    submit_phone_number,
)


class NoIdentityActivityExpected:
    """Fail if this representation scenario crosses into identity behavior."""

    def lookup_by_phone_number(self, internal_value: str) -> None:
        pytest.fail(
            "IT-10R1S4 does not authorize human-identity lookup behavior."
        )

    def create_for_phone_number(self, internal_value: str) -> None:
        pytest.fail(
            "IT-10R1S4 does not authorize human-identity creation behavior."
        )


def test_it_10_r1_s4_uses_only_the_numeric_representation_inside_service() -> None:
    """Use one canonical numeric value internally and format only for a form."""

    form_value = "+1-999-999-9999"
    internal_value = submit_phone_number(
        form_value,
        NoIdentityActivityExpected(),
    )

    stored_phone_numbers = {internal_value}
    records_by_phone_number = {internal_value: "customer-account-record"}

    assert internal_value == "19999999999"
    assert len(internal_value) == 11
    assert set(internal_value) <= set("0123456789")
    assert not set(internal_value) & set("+- ()")

    lookup_value = normalize_phone_number(form_value)
    assert lookup_value in stored_phone_numbers
    assert records_by_phone_number[lookup_value] == "customer-account-record"
    assert lookup_value == internal_value
    assert all(character in "0123456789" for character in internal_value)

    displayed_value = format_phone_number_for_form(internal_value)
    assert displayed_value == form_value
    assert displayed_value != internal_value
    assert internal_value == "19999999999"
