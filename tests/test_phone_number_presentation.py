"""Executable test for IT-10R1S3 phone-number presentation."""

from __future__ import annotations

from importlib import import_module
from typing import Any


PHONE_NUMBER_MODULE = "app.services.phone_numbers"
FORMATTER_NAME = "format_phone_number_for_form"


def _form_formatter() -> Any:
    """Load the form-presentation contract expected by IT-10R1S3."""

    module = import_module(PHONE_NUMBER_MODULE)
    formatter = getattr(module, FORMATTER_NAME, None)
    assert callable(formatter), (
        "IT-10R1S3 requires "
        "app.services.phone_numbers.format_phone_number_for_form"
        "(internal_value)."
    )
    return formatter


def test_it_10_r1_s3_formats_an_internal_country_code_1_phone_number() -> None:
    """Present a formatted value without replacing the internal value."""

    internal_value = "19999999999"

    displayed_value = _form_formatter()(internal_value)

    assert displayed_value == "+1-999-999-9999"
    assert displayed_value != internal_value
    assert internal_value == "19999999999"
