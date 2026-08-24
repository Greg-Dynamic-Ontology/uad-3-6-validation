"""Phone-number representation services."""

from __future__ import annotations


FORMATTING_CHARACTERS = "+- ()"
FORMATTING_TRANSLATION = str.maketrans("", "", FORMATTING_CHARACTERS)
ASCII_DECIMAL_DIGITS = frozenset("0123456789")


class InvalidPhoneNumberError(ValueError):
    """Report a form value that cannot become an internal phone number."""


def normalize_phone_number(form_value: str) -> str:
    """Remove form formatting from a phone number's internal representation.

    Validation is deliberately separate from normalization. Characters that
    are not recognized formatting characters remain available to the
    validation behavior to accept or reject.
    """

    return form_value.translate(FORMATTING_TRANSLATION)


def submit_phone_number(form_value: str, identity_gateway: object) -> str:
    """Validate a form submission before any human-identity activity."""

    internal_value = normalize_phone_number(form_value)
    is_internal_phone_number = (
        len(internal_value) == 11
        and set(internal_value) <= ASCII_DECIMAL_DIGITS
    )

    if not is_internal_phone_number:
        raise InvalidPhoneNumberError(
            "A phone number with country calling code is required."
        )

    return internal_value


def format_phone_number_for_form(internal_value: str) -> str:
    """Format a country-code-1 internal value for display on a form."""

    return (
        f"+{internal_value[0]}-{internal_value[1:4]}-"
        f"{internal_value[4:7]}-{internal_value[7:11]}"
    )