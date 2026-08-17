"""Report XML Schema component-processing coverage."""

from collections import Counter

from app.models.schema_model import SchemaModel
from app.models.schema_processing import (
    ComponentKindCoverage,
    ComponentProcessingCoverageReport,
    ComponentProcessingStatus,
)


def report_component_processing_coverage(
    schema: SchemaModel,
) -> ComponentProcessingCoverageReport:
    """Compare discovered occurrences with explicit dispositions."""

    processed_counts = Counter(
        disposition.component_kind
        for disposition in schema.processing_dispositions
        if disposition.processed
    )
    rows = tuple(
        _coverage_row(
            component_kind=component_kind,
            found=found,
            processed=processed_counts[component_kind],
        )
        for component_kind, found in sorted(
            schema.component_counts.items()
        )
    )
    return ComponentProcessingCoverageReport(component_kinds=rows)


def _coverage_row(
    *,
    component_kind: str,
    found: int,
    processed: int,
) -> ComponentKindCoverage:
    """Classify one component kind from its occurrence counts."""

    if found < 0 or processed < 0:
        raise ValueError("Component counts must not be negative.")
    if processed > found:
        raise ValueError("Processed count must not exceed found count.")

    if processed == 0:
        status = ComponentProcessingStatus.NOT_PROCESSED
    elif processed < found:
        status = ComponentProcessingStatus.INCOMPLETE
    else:
        status = ComponentProcessingStatus.PROCESSED

    return ComponentKindCoverage(
        component_kind=component_kind,
        found=found,
        processed=processed,
        status=status,
    )
