"""Executable tests for IT-10R1S2 phone-number rejection."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest


PHONE_NUMBER_MODULE = "app.services.phone_numbers"
SUBMISSION_SERVICE_NAME = "submit_phone_number"
VALIDATION_ERROR_NAME = "InvalidPhoneNumberError"


class IdentityGatewaySpy:
    """Record forbidden identity activity during invalid form submission."""

    def __init__(self) -> None:
        self.lookup_calls: list[str] = []
        self.creation_calls: list[str] = []

    def lookup_by_phone_number(self, internal_value: str) -> Any:
        self.lookup_calls.append(internal_value)
        pytest.fail("An invalid phone number must not trigger identity lookup.")

    def create_for_phone_number(self, internal_value: str) -> Any:
        self.creation_calls.append(internal_value)
        pytest.fail("An invalid phone number must not trigger identity creation.")


def _submission_contract() -> tuple[Any, type[Exception]]:
    """Load the form-submission contract expected by IT-10R1S2."""

    module = import_module(PHONE_NUMBER_MODULE)
    submission_service = getattr(module, SUBMISSION_SERVICE_NAME, None)
    validation_error = getattr(module, VALIDATION_ERROR_NAME, None)

    assert callable(submission_service), (
        "IT-10R1S2 requires "
        "app.services.phone_numbers.submit_phone_number(form_value, "
        "identity_gateway)."
    )
    assert isinstance(validation_error, type) and issubclass(
        validation_error,
        Exception,
    ), (
        "IT-10R1S2 requires "
        "app.services.phone_numbers.InvalidPhoneNumberError."
    )
    return submission_service, validation_error


@pytest.mark.parametrize(
    "form_value",
    [
        "+1-999-999-999",
        "+1-999-999-99999",
        "+1-999-ABC-9999",
    ],
    ids=["fewer-than-11-digits", "more-than-11-digits", "alphabetic-characters"],
)
def test_it_10_r1_s2_rejects_an_invalid_form_phone_number(
    form_value: str,
) -> None:
    """Reject invalid input before looking up or creating a human identity."""

    submit_phone_number, invalid_phone_number_error = _submission_contract()
    identity_gateway = IdentityGatewaySpy()

    with pytest.raises(invalid_phone_number_error) as caught_error:
        submit_phone_number(form_value, identity_gateway)

    assert "country calling code" in str(caught_error.value).lower()
    assert identity_gateway.lookup_calls == []
    assert identity_gateway.creation_calls == []
