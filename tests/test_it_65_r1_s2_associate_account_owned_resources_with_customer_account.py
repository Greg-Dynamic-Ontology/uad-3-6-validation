"""IT-65R1S2: customer accounts own credits and validation work.

Service-boundary test; repository doubles do not establish GraphDB integration.
Authenticated identity and active account context are supplied prerequisites.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from types import SimpleNamespace

from app.services.customer_accounts import CustomerAccountMembership, CustomerAccountRole
from app.services.validation_credits import issue_validation_credits
from app.services.customer_validation_resources import assign_customer_validation_resource_ownership


@dataclass
class CreditRepository:
    lots: list = field(default_factory=list)

    def add(self, credit_lot):
        self.lots.append(deepcopy(credit_lot))

    def save(self, credit_lot):
        for index, existing in enumerate(self.lots):
            if existing.validation_credit_lot_id == credit_lot.validation_credit_lot_id:
                self.lots[index] = deepcopy(credit_lot)
                return
        raise AssertionError("Cannot update a credit lot that has not been added.")


@dataclass
class ResourceRepository:
    reports: list = field(default_factory=list)
    cycles: list = field(default_factory=list)

    def add_report_artifact(self, report_artifact):
        self.reports.append(deepcopy(report_artifact))

    def add_validation_cycle(self, validation_cycle):
        self.cycles.append(deepcopy(validation_cycle))

    def list_report_artifacts(self):
        return tuple(deepcopy(self.reports))

    def list_validation_cycles(self):
        return tuple(deepcopy(self.cycles))


@dataclass
class CreditHistory:
    events: list = field(default_factory=list)

    def record(self, **event):
        self.events.append(deepcopy(event))


@dataclass
class CreditIds:
    sequence: int = 0

    def new_validation_credit_lot_id(self):
        self.sequence += 1
        return f"credit-lot-it65-{self.sequence}"


def test_it_65_r1_s2_associate_account_owned_resources_with_customer_account():
    # The same authenticated user is authorized in two active accounts. This
    # prevents a user-keyed implementation from accidentally passing the test.
    actor_id = "uad-user-it65-shared-administrator"
    workos_user_id = "user_it65_shared_workos_identity"
    account_ids = ("customer-account-it65-a", "customer-account-it65-b")
    credits = CreditRepository()
    resources = ResourceRepository()
    history = CreditHistory()
    ids = CreditIds()

    for index, account_id in enumerate(account_ids, start=1):
        purchaser = CustomerAccountMembership(
            human_user_id=actor_id,
            customer_account_id=account_id,
            role=CustomerAccountRole.BILLING_ADMINISTRATOR,
            active=True,
        )
        payment = SimpleNamespace(
            payment_id=f"payment-it65-{index}",
            customer_account_id=account_id,
            status="completed",
        )
        lot = issue_validation_credits(
            payment=payment, purchaser=purchaser, quantity=10 * index,
            id_generator=ids, credit_repository=credits, credit_history=history,
        )
        owned = assign_customer_validation_resource_ownership(
            actor_id=actor_id,
            customer_account_id=account_id,
            report_artifact=SimpleNamespace(report_artifact_id=f"report-it65-{index}"),
            validation_cycle=SimpleNamespace(validation_cycle_id=f"cycle-it65-{index}"),
            repository=resources,
        )
        for resource in (lot, owned.report_artifact, owned.validation_cycle):
            assert resource.customer_account_id == account_id, (
                "IT-65R1S2 requires ownership by the customer-account ID."
            )
            assert resource.customer_account_id not in {actor_id, workos_user_id}, (
                "The acting user's identity must not become the resource owner."
            )
        assert owned.report_artifact.actor_id == actor_id
        assert owned.validation_cycle.actor_id == actor_id

    # Inspect saved snapshots independently of service return values.
    assert len(credits.lots) == len(resources.reports) == len(resources.cycles) == 2
    for index, account_id in enumerate(account_ids, start=1):
        lots = [lot for lot in credits.lots if lot.customer_account_id == account_id]
        reports = [item for item in resources.list_report_artifacts() if item.customer_account_id == account_id]
        cycles = [item for item in resources.list_validation_cycles() if item.customer_account_id == account_id]
        assert len(lots) == len(reports) == len(cycles) == 1
        assert lots[0].payment_id == f"payment-it65-{index}"
        assert lots[0].remaining_quantity == 10 * index
        assert reports[0].report_artifact_id == f"report-it65-{index}"
        assert cycles[0].validation_cycle_id == f"cycle-it65-{index}"
        events = [event for event in history.events if event.get("customer_account_id") == account_id]
        assert len(events) == 1
        assert events[0]["actor_id"] == actor_id
        assert events[0]["validation_credit_lot_id"] == lots[0].validation_credit_lot_id

    for resource in credits.lots + resources.reports + resources.cycles:
        assert resource.customer_account_id in account_ids
