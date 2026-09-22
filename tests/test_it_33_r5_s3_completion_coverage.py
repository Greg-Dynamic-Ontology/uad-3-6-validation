"""IT-33R5S3 — Complete the iteration with explicit coverage."""

import csv
import json
import logging
from collections import Counter
from pathlib import Path

from app.services import required_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    PROJECT_ROOT
    / "data"
    / "uad36-test-suite"
    / "tests"
    / "fixtures"
    / "required_data"
)


def test_it_33_r5_s3_completion_coverage(caplog, record_property):
    """
    Audit the agreed selected subset independently of loader output.

    The acceptance suite verifies behavior and regression status.
    This test does not recursively run pytest or claim completion alone.
    """
    selected_rows = json.loads(
        (FIXTURES / "selected-workbook-rows.json").read_text(
            encoding="utf-8-sig"
        )
    )
    with (FIXTURES / "manifest.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        cases = list(csv.DictReader(stream))

    selected_counts = Counter(row["Unique ID"] for row in selected_rows)
    manifest_counts = Counter(case["row_id"] for case in cases)
    selected_ids = set(selected_counts)
    manifest_ids = set(manifest_counts)

    problems = []

    if not selected_ids:
        problems.append("The agreed selected inventory is empty.")

    for row_id, count in sorted(selected_counts.items()):
        if count != 1:
            problems.append(f"{row_id}: duplicate selected inventory rows.")

    for row_id, count in sorted(manifest_counts.items()):
        if count != 1:
            problems.append(
                f"{row_id}: expected one controlled missing-data fixture; "
                f"found {count} manifest entries."
            )

    for row_id in sorted(selected_ids - manifest_ids):
        problems.append(f"{row_id}: missing fixture coverage.")

    for row_id in sorted(manifest_ids - selected_ids):
        problems.append(f"{row_id}: fixture outside the agreed subset.")

    required_data.load_required_rules.cache_clear()
    try:
        with caplog.at_level(
            logging.ERROR, logger=required_data.__name__
        ):
            rules = required_data.load_required_rules()

        supported = {row["Unique ID"]: row for row in rules}

        for row_id in sorted(selected_ids - set(supported)):
            problems.append(
                f"{row_id}: agreed required-data row was not loaded; "
                "resolve its configuration or explicitly review its scope."
            )

        configuration_errors = [
            record.getMessage()
            for record in caplog.records
            if record.name == required_data.__name__
            and record.levelno >= logging.ERROR
        ]
        problems.extend(configuration_errors)

        coverage = []
        for case in cases:
            row_id = case["row_id"]
            fixture = FIXTURES / "tests" / case["filename"]
            exists = fixture.is_file()
            coverage.append({
                "row_id": row_id,
                "fixture": case["filename"],
                "file_exists": exists,
                "loaded": row_id in supported,
            })

            if not exists:
                problems.append(
                    f"{row_id}: fixture file missing: {case['filename']}"
                )

            rule = supported.get(row_id)
            if rule is not None:
                for manifest_field, source_field in (
                    ("rule_id", "Message ID"),
                    ("primary_data_element", "Primary Data Element"),
                    ("property_affected", "Property Affected"),
                ):
                    if case[manifest_field] != rule[source_field]:
                        problems.append(
                            f"{row_id}: manifest {manifest_field} "
                            "does not match the loaded source rule."
                        )

        baseline = FIXTURES / "baseline" / "SF1_Appraisal_v1.4.xml"
        if not baseline.is_file():
            problems.append("The positive-control XML file is missing.")

        record_property(
            "required_data_coverage",
            json.dumps(coverage, sort_keys=True),
        )
        record_property(
            "completion_blockers",
            json.dumps(problems),
        )
        record_property(
            "coverage_scope",
            "Selected required-data inventory only; "
            "fixture presence does not establish behavioral success.",
        )

        assert not problems, (
            "IT-33 completion is blocked:\n" + "\n".join(problems)
        )
    finally:
        required_data.load_required_rules.cache_clear()