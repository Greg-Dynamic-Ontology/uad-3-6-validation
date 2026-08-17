"""Acceptance test for IT-5R7S3 deterministic reprocessing."""

from pathlib import Path

from app.models.schema_model import SchemaModel
from app.models.schema_processing import (
    ComponentProcessingCoverageReport,
)
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader.processing_coverage import (
    report_component_processing_coverage,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMBINED_SCHEMA_PATH = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)


def test_reprocessing_produces_equivalent_model_and_coverage() -> None:
    """Load the same closure twice and compare independent results."""

    first_model, first_coverage = _process_uad_schema()
    second_model, second_coverage = _process_uad_schema()

    assert first_model is not second_model
    assert first_model == second_model
    assert first_model.processing_dispositions == (
        second_model.processing_dispositions
    )
    assert first_coverage == second_coverage
    assert first_coverage is not second_coverage


def _process_uad_schema() -> tuple[
    SchemaModel,
    ComponentProcessingCoverageReport,
]:
    model = SchemaLoader().load(COMBINED_SCHEMA_PATH)
    coverage = report_component_processing_coverage(model)
    return model, coverage
