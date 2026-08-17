"""Component-processing coverage returned to Developer mode."""

from dataclasses import asdict, dataclass
from enum import StrEnum


class ComponentProcessingStatus(StrEnum):
    """Coverage status for one XML Schema component kind."""

    NOT_PROCESSED = "NP"
    INCOMPLETE = "Incomplete"
    PROCESSED = "Processed"


@dataclass(frozen=True, slots=True)
class ComponentKindCoverage:
    """Found and processed occurrence counts for one component kind."""

    component_kind: str
    found: int
    processed: int
    status: ComponentProcessingStatus


@dataclass(frozen=True, slots=True)
class ComponentProcessingCoverageReport:
    """Coverage rows for one loaded schema closure."""

    component_kinds: tuple[ComponentKindCoverage, ...]

    def as_response(self) -> dict[str, list[dict[str, object]]]:
        """Return a JSON-ready representation."""

        return {
            "component_kinds": [
                asdict(component_kind)
                for component_kind in self.component_kinds
            ]
        }
