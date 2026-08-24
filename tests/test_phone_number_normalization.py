"""Executable tests for IT-10R1S1 phone-number normalization."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module

import pytest


NORMALIZER_MODULE = "app.services.phone_numbers"
NORMALIZER_NAME = "normalize_phone_number"


def _phone_number_normalizer() -> Callable[[str], str]:
    """Load the service contract without requiring an implementation to exist yet."""

    try:
        module = import_module(NORMALIZER_MODULE)
    except ModuleNotFoundError as error:
        if error.name != NORMALIZER_MODULE:
            raise
        pytest.fail(
            "IT-10R1S1 requires app.services.phone_numbers before the "
            "normalization behavior can become green.",
            pytrace=False,
        )

    normalizer = getattr(module, NORMALIZER_NAME, None)
    assert callable(normalizer), (
        "IT-10R1S1 requires the service contract "
        "app.services.phone_numbers.normalize_phone_number(form_value)."
    )
    return normalizer


@pytest.mark.parametrize(
    ("form_value", "expected_internal_value"),
    [
        ("+1-999-999-9999", "19999999999"),
        ("+1-999-999-9977", "19999999977"),
    ],
    ids=["general-country-code-1-number", "designated-developer-number"],
)
def test_it_10_r1_s1_normalizes_a_form_phone_number(
    form_value: str,
    expected_internal_value: str,
) -> None:
    """Normalize each specified form value to its exact internal value."""

    internal_value = _phone_number_normalizer()(form_value)

    assert internal_value == expected_internal_value
    assert len(internal_value) == 11
    assert set(internal_value) <= set("0123456789")
    assert not set(internal_value) & set("+- ()")
