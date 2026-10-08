"""IT-2R1S3: both account kinds enforce the same display-name requirement.

Each case attempts both account kinds and compares their rejection reasons.
Company existence is a supplied precondition; WorkOS is outside this test.
"""

from dataclasses import dataclass, field

import pytest

from app.services.user_accounts import UserAccount, create_user_account


class UserAccountIdGeneratorStub:
    def new_user_account_id(self) -> str:
        return "user-account-under-test"


@dataclass
class UserAccountRepositorySpy:
    companies: dict[str, str] = field(
        default_factory=lambda: {"company-1": "Example Appraisals"}
    )
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def add(self, user_account: UserAccount) -> None:
        self.saved_accounts.append(user_account)


@pytest.mark.parametrize(
    "invalid_data",
    [{}, {"display_name": ""}, {"display_name": " \t\r\n "}],
    ids=["missing-display-name", "empty-display-name", "whitespace-display-name"],
)
def test_it_2_r1_s3_shared_user_data_requirements(invalid_data: dict[str, str]) -> None:
    outcomes = []
    for company_id in (None, "company-1"):
        repository = UserAccountRepositorySpy()
        if company_id is not None:
            assert company_id in repository.companies
        supplied = dict(invalid_data)
        rejection = None
        try:
            create_user_account(
                user_data=supplied,
                company_id=company_id,
                id_generator=UserAccountIdGeneratorStub(),
                account_repository=repository,
            )
        except ValueError as error:
            rejection = error
        outcomes.append((company_id, repository, supplied, rejection))

    # Check both attempts after execution, so RED does not stop at the first kind.
    accepted = [
        "single-user" if company_id is None else "company-user"
        for company_id, _, _, error in outcomes if error is None
    ]
    assert not accepted, (
        "IT-2R1S3: expected rejection of invalid display_name; "
        f"creation accepted: {', '.join(accepted)}"
    )
    for company_id, repository, supplied, error in outcomes:
        assert repository.saved_accounts == [], (
            f"IT-2R1S3: rejected data was saved for company_id={company_id!r}"
        )
        assert supplied == invalid_data, "Rejected creation changed supplied data."
        assert "display_name" in str(error), "Rejection must identify the unmet field."

    single_error, company_error = outcomes[0][3], outcomes[1][3]
    assert type(single_error) is type(company_error)
    assert str(single_error) == str(company_error), (
        "Both account kinds must report the same unmet user-data requirement."
    )
