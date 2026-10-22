"""IT-33R4S2: repeat evaluation with unchanged workbook-derived inputs."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

from app.models.enums import Investor
from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION = ROOT / "config" / "configuration.ttl"


def governed_content(finding):
    """Exclude run metadata, preserving all governed finding content."""
    return finding.model_dump(
        mode="json",
        exclude={
            "finding_id": True,
            "source": {"ingestion_timestamp"},
        },
    )


def test_it_33_r4_s2_repeat_evaluation(monkeypatch):
    """Return identical governed findings in stable, duplicate-free order."""
    selected_ids = ["0100.0009", "0100.0007"]

    workbook = read_active_compliance_workbook_rows(
        configuration_path=CONFIGURATION,
    )
    source_rows = {}
    for row_id in selected_ids:
        matches = [
            row for row in workbook.rows
            if row["Unique ID"] == row_id
        ]
        assert len(matches) == 1, (
            f"The published workbook must contain exactly one {row_id}."
        )
        source_rows[row_id] = dict(matches[0])

    # Deliberately reverse row-ID order to test output ordering.
    selected_workbook = replace(
        workbook,
        rows=tuple(source_rows[row_id] for row_id in selected_ids),
    )
    original_source_rows = deepcopy(selected_workbook.rows)

    def read_selected_workbook(*, configuration_path):
        assert Path(configuration_path).resolve() == CONFIGURATION.resolve()
        return selected_workbook

    def qname(name):
        return f"{{{required_data.NAMESPACE}}}{name}"

    root = ET.Element(qname("MESSAGE"))
    analysis = ET.SubElement(root, qname("VALUATION_ANALYSIS"))
    properties = ET.SubElement(analysis, qname("PROPERTIES"))

    # Both required elements are absent in two distinct occurrences.
    for _ in range(2):
        subject = ET.SubElement(
            properties,
            qname("PROPERTY"),
            {"ValuationUseType": "SubjectProperty"},
        )
        ET.SubElement(subject, qname("ADDRESS"))

    original_xml = ET.tostring(root)
    required_data.load_required_rules.cache_clear()

    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                required_data,
                "read_active_compliance_workbook_rows",
                read_selected_workbook,
            )

            # Keep the real production loader and its cache.
            original_rules = deepcopy(required_data.load_required_rules())
            runs = []

            for reload_inventory in (False, False, True):
                if reload_inventory:
                    required_data.load_required_rules.cache_clear()

                findings = required_data.evaluate_required_data(
                    root, Investor.BOTH
                )
                runs.append([governed_content(f) for f in findings])

                assert len(findings) == 4
                keys = [
                    (finding.row_id, finding.data_location)
                    for finding in findings
                ]
                assert len(set(keys)) == 4, (
                    "Duplicate findings were emitted."
                )

                assert ET.tostring(root) == original_xml
                assert selected_workbook.rows == original_source_rows
                assert required_data.load_required_rules() == original_rules

            assert runs[0] == runs[1] == runs[2], (
                "Unchanged inputs must produce identical governed content "
                "and finding order, including after reloading the inventory."
            )

            prefix = "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
            expected_keys = [
                (
                    row_id,
                    prefix
                    + f"m:PROPERTY[{position}]"
                    + "[@ValuationUseType='SubjectProperty']"
                    + f"/m:ADDRESS/m:{element}",
                )
                for row_id, element in [
                    ("0100.0007", "AddressLineText"),
                    ("0100.0009", "CityName"),
                ]
                for position in (1, 2)
            ]

            actual_keys = [
                (finding["row_id"], finding["data_location"])
                for finding in runs[0]
            ]
            assert actual_keys == expected_keys, (
                "Findings must be ordered by source row ID and affected "
                "context occurrence, rather than inventory input order."
            )
    finally:
        required_data.load_required_rules.cache_clear()