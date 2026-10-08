"""IT-2R2S1: reject a company link that has no matching company record.

The repository contains another company to distinguish checking the requested
identifier from merely checking whether any company exists.
"""

from dataclasses import dataclass, field

from app.services.user_accounts import UserAccount, create_user_account


class UserAccountIdGeneratorStub:
    def new_user_account_id(self) -> str:
        return "user-account-under-test"


@dataclass
class AccountRepositorySpy:
    companies: dict[str, str] = field(
        default_factory=lambda: {"company-existing": "Existing Appraisals"}
    )
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def company_exists(self, company_id: str) -> bool:
        return company_id in self.companies

    def add(self, user_account: UserAccount) -> None:
        self.saved_accounts.append(user_account)


def test_it_2_r2_s1_reject_nonexistent_company() -> None:
    repository = AccountRepositorySpy()
    company_id = "company-missing"
    assert not repository.company_exists(company_id)
    user_data = {"display_name": "Alex Example"}
    original_data = dict(user_data)
    original_companies = dict(repository.companies)

    rejection = None
    try:
        create_user_account(
            user_data=user_data,
            company_id=company_id,
            id_generator=UserAccountIdGeneratorStub(),
            account_repository=repository,
        )
    except ValueError as error:
        rejection = error

    assert rejection is not None, (
        "IT-2R2S1: creation accepted a link to a nonexistent company."
    )
    assert repository.saved_accounts == [], "Rejected creation saved an account."
    message = str(rejection).casefold()
    assert "company" in message and (
        "does not exist" in message or "not found" in message
        or "nonexistent" in message
    ), "Rejection must explain that the company does not exist."
    assert user_data == original_data
    assert repository.companies == original_companies
