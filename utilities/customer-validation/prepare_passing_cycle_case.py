"""Create a dated, verified passing test copy of the published SF1 report."""
import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    sys.path.insert(0, str(root))
    from app.models.validation import ValidationRequest
    from app.services.validation import ValidationService
    from app.services.required_data import load_required_rules
    from app.services.account_cycle_validation import current_coverage

    source = root / "specs/fannie-mae/Appendix D-1 SF1_Appraisal/SF1_Appraisal_v1.4.xml"
    source_bytes = source.read_bytes()
    original = source_bytes.decode("utf-8-sig")
    tree = ET.fromstring(original)
    ns = "{http://www.mismo.org/residential/2009/schemas}"
    effective = tree.find(".//" + ns + "AppraisalReportEffectiveDate")
    if effective is None or not effective.text:
        raise ValueError("Published SF1 effective date is missing.")
    anchor = date.today() - timedelta(days=1)  # Avoid UTC/local-midnight future-date drift.
    offset = anchor - date.fromisoformat(effective.text)
    edits = []

    def shift(match):
        old = date.fromisoformat(match.group())
        updated = (old + offset).isoformat()
        edits.append({"before": old.isoformat(), "after": updated})
        return updated

    # Preserve the exact XML layout and namespaces. Shift all lexical dates by
    # one offset so the original temporal relationships are retained.
    content = re.sub(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", shift, original).encode("utf-8")
    output = (args.output_directory or root / "tests/fixtures/it_64/r2/s2").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "sf1-controlled-current-dates.xml"
    if any((output / name).exists() for name in (report_path.name, "passing-case.json", "fixture-provenance.json")):
        raise ValueError("Fixture output already exists. Use a new --output-directory to retain earlier evidence.")
    load_required_rules.cache_clear()
    before = current_coverage()
    result = ValidationService().validate(ValidationRequest(package_name=report_path.name, xml_text=content.decode("utf-8")))
    if result.processing_status != "completed" or not result.passed or result.findings:
        raise ValueError("Candidate does not pass current coverage: " + repr([(f.rule_id, f.finding, f.observed_value) for f in result.findings]))
    if current_coverage() != before:
        raise ValueError("Coverage changed during fixture verification.")
    if source.read_bytes() != source_bytes:
        raise ValueError("Published source changed during fixture preparation.")
    manifest = {"report_path": report_path.name, "report_sha256": sha256(content).hexdigest(), **before}
    report_path.write_bytes(content)
    (output / "passing-case.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "fixture-provenance.json").write_text(json.dumps({
        "source": str(source), "source_sha256": sha256(source_bytes).hexdigest(),
        "date_anchor_local": anchor.isoformat(), "offset_days": offset.days,
        "date_edits": edits, "production_result": result.model_dump(mode="json", by_alias=True),
        "scope_note": "Pass verified against the listed current supported rules; governed XSD assessment executed; SHACL not executed.",
        "expiry_note": "Date-sensitive fixture: reverify before use; create a new version when it ages out.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(edits)} date shifts; zero production findings.")
    print(f"Passing-case manifest: {output / 'passing-case.json'}")
    print("Published source unchanged. No account or credits changed.")


if __name__ == "__main__":
    main()
