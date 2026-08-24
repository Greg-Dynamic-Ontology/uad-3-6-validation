"""Executable tests for IT-11R1S1 human-user registration state."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


HUMAN_USER_MODULE = "app.services.human_users"
REGISTRATION_SERVICE_NAME = "determine_registration_state"
REGISTRATION_STATE_NAME = "HumanUserRegistrationState"


@dataclass
class HumanUserRepositorySpy:
    """Return a configured lookup result and record phone-only access."""

    human_user: object | None
    lookup_calls: list[str] = field(default_factory=list)

    def find_by_phone_number(self, internal_phone_number: str) -> object | None:
        self.lookup_calls.append(internal_phone_number)
        return self.human_user


def _registration_contract() -> tuple[Any, Any]:
    """Load the human-user lookup contract expected by IT-11R1S1."""

    try:
        module = import_module(HUMAN_USER_MODULE)
    except ModuleNotFoundError as error:
        if error.name != HUMAN_USER_MODULE:
            raise
        pytest.fail(
            "IT-11R1S1 requires app.services.human_users before human-user "
            "registration state can become green.",
            pytrace=False,
        )

    registration_service = getattr(
        module,
        REGISTRATION_SERVICE_NAME,
        None,
    )
    registration_state = getattr(module, REGISTRATION_STATE_NAME, None)

    assert callable(registration_service), (
        "IT-11R1S1 requires "
        "app.services.human_users.determine_registration_state"
        "(internal_phone_number, human_user_repository)."
    )
    assert registration_state is not None, (
        "IT-11R1S1 requires "
        "app.services.human_users.HumanUserRegistrationState."
    )
    return registration_service, registration_state


@pytest.mark.parametrize(
    ("existing_human_user", "expected_state_name"),
    [
        (object(), "EXISTING_USER"),
        (None, "NEW_USER"),
    ],
    ids=["existing-human-user", "new-human-user"],
)
def test_it_11_r1_s1_determines_registration_state_from_phone_number_only(
    existing_human_user: object | None,
    expected_state_name: str,
) -> None:
    """Determine existing/new state without other identity or account data."""

    determine_registration_state, registration_state = _registration_contract()
    repository = HumanUserRepositorySpy(existing_human_user)
    internal_phone_number = "19999999999"

    actual_state = determine_registration_state(
        internal_phone_number,
        repository,
    )

    assert actual_state is getattr(registration_state, expected_state_name)
    assert repository.lookup_calls == [internal_phone_number]
