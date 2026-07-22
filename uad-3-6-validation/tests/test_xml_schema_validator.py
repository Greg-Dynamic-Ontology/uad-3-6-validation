from pathlib import Path

from app.models.schema_validation import SchemaValidationStatus
from app.services.xml_schema_validator import validate_xml_schema


VALID_SCHEMA = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    elementFormDefault="qualified">

    <xs:element name="Appraisal">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="Identifier" type="xs:string"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>

</xs:schema>
"""


VALID_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Appraisal>
    <Identifier>APP-001</Identifier>
</Appraisal>
"""


SCHEMA_INVALID_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Appraisal>
    <UnexpectedElement>APP-001</UnexpectedElement>
</Appraisal>
"""


MALFORMED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Appraisal>
    <Identifier>APP-001</Identifier>
"""


def write_text_file(
    directory: Path,
    filename: str,
    content: str,
) -> Path:
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_xml_produces_passing_schema_validation_report(
    tmp_path: Path,
) -> None:
    schema_path = write_text_file(
        tmp_path,
        "uad-test-schema.xsd",
        VALID_SCHEMA,
    )
    xml_path = write_text_file(
        tmp_path,
        "valid-appraisal.xml",
        VALID_XML,
    )

    report = validate_xml_schema(
        xml_path=xml_path,
        schema_path=schema_path,
        schema_version="test-schema-1.0",
    )

    assert report.package_name == "valid-appraisal.xml"
    assert report.schema_name == "uad-test-schema.xsd"
    assert report.schema_version == "test-schema-1.0"

    assert report.well_formed is True
    assert report.status == SchemaValidationStatus.PASSED
    assert report.schema_valid is True

    assert report.summary.warning_count == 0
    assert report.summary.error_count == 0
    assert report.summary.finding_count == 0
    assert report.findings == []


def test_schema_invalid_xml_produces_failing_report(
    tmp_path: Path,
) -> None:
    schema_path = write_text_file(
        tmp_path,
        "uad-test-schema.xsd",
        VALID_SCHEMA,
    )
    xml_path = write_text_file(
        tmp_path,
        "schema-invalid-appraisal.xml",
        SCHEMA_INVALID_XML,
    )

    report = validate_xml_schema(
        xml_path=xml_path,
        schema_path=schema_path,
        schema_version="test-schema-1.0",
    )

    assert report.well_formed is True
    assert report.status == SchemaValidationStatus.FAILED
    assert report.schema_valid is False

    assert report.summary.error_count >= 1
    assert report.summary.finding_count == len(report.findings)

    finding = report.findings[0]

    assert finding.message
    assert finding.line is not None
    assert finding.line >= 1


def test_malformed_xml_produces_report_instead_of_raising_exception(
    tmp_path: Path,
) -> None:
    schema_path = write_text_file(
        tmp_path,
        "uad-test-schema.xsd",
        VALID_SCHEMA,
    )
    xml_path = write_text_file(
        tmp_path,
        "malformed-appraisal.xml",
        MALFORMED_XML,
    )

    report = validate_xml_schema(
        xml_path=xml_path,
        schema_path=schema_path,
        schema_version="test-schema-1.0",
    )

    assert report.well_formed is False
    assert report.status == SchemaValidationStatus.FAILED
    assert report.schema_valid is False

    assert report.summary.error_count >= 1
    assert report.summary.finding_count == len(report.findings)

    finding = report.findings[0]

    assert finding.message
    assert finding.line is not None
    assert finding.line >= 1


def test_each_schema_error_becomes_a_finding(
    tmp_path: Path,
) -> None:
    schema_path = write_text_file(
        tmp_path,
        "uad-test-schema.xsd",
        VALID_SCHEMA,
    )

    xml_with_multiple_errors = """\
<?xml version="1.0" encoding="UTF-8"?>
<Appraisal>
    <UnexpectedElement>unexpected</UnexpectedElement>
    <AnotherUnexpectedElement>unexpected</AnotherUnexpectedElement>
</Appraisal>
"""

    xml_path = write_text_file(
        tmp_path,
        "multiple-errors.xml",
        xml_with_multiple_errors,
    )

    report = validate_xml_schema(
        xml_path=xml_path,
        schema_path=schema_path,
    )

    assert report.status == SchemaValidationStatus.FAILED
    assert report.summary.error_count == len(report.findings)
    assert report.summary.error_count >= 1

    for finding in report.findings:
        assert finding.message
        assert finding.line is not None
        assert finding.line >= 1


def test_validation_report_contains_a_unique_report_identifier(
    tmp_path: Path,
) -> None:
    schema_path = write_text_file(
        tmp_path,
        "uad-test-schema.xsd",
        VALID_SCHEMA,
    )
    xml_path = write_text_file(
        tmp_path,
        "valid-appraisal.xml",
        VALID_XML,
    )

    first_report = validate_xml_schema(
        xml_path=xml_path,
        schema_path=schema_path,
    )
    second_report = validate_xml_schema(
        xml_path=xml_path,
        schema_path=schema_path,
    )

    assert first_report.report_id
    assert second_report.report_id
    assert first_report.report_id != second_report.report_id