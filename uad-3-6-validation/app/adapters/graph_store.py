from app.models.common import GraphResource
from app.models.rules import ValidationRule


class InMemoryGraphStore:
    def __init__(self) -> None:
        self.resources: dict[str, GraphResource] = {}
        self.rules: dict[str, ValidationRule] = {}

    def put_resource(self, resource: GraphResource) -> GraphResource:
        self.resources[resource.resource_id] = resource
        return resource

    def get_resource(self, resource_id: str) -> GraphResource | None:
        return self.resources.get(resource_id)

    def put_rule(self, rule: ValidationRule) -> ValidationRule:
        self.rules[rule.rule_id] = rule
        return rule

    def list_rules(self) -> list[ValidationRule]:
        return list(self.rules.values())

    def get_rule(self, rule_id: str) -> ValidationRule | None:
        return self.rules.get(rule_id)

    def find_schema_element(self, element_name: str) -> GraphResource | None:
        for resource in self.resources.values():
            if resource.resource_type == "schema_element" and resource.label == element_name:
                return resource
        return None


graph_store = InMemoryGraphStore()
