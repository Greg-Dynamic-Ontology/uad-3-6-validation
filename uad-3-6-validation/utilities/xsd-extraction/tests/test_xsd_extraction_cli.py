"""Black-box specification tests for the XSD Extraction CLI.

These tests exercise the public command-line contract documented in README.md.
They intentionally do not depend on the utility's internal Python API.

Expected location:

    utilities/
        xsd-extraction/
            README.md
            xsd_extraction/
                __main__.py
            tests/
                test_cli.py

Run from the xsd-extraction directory with:

    python -m pytest
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"


def run_cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the CLI exactly as a user would run it."""
    return subprocess.run(
        [sys.executable, "-m", "xsd_extraction", *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return stdout and stderr as one searchable string."""
    return f"{result.stdout}\n{result.stderr}"


def write_schema(
    path: Path,
    *,
    prefix: str = "xsd",
    declaration: str = XML_DECLARATION,
    schema_attributes: str = "",
    body: str = "",
) -> None:
    """Create an XSD fixture satisfying the documented two-line preamble."""
    attributes = schema_attributes.strip()
    if attributes:
        attributes = f" {attributes}"

    path.write_text(
        "\n".join(
            [
                declaration,
                (
                    f'<{prefix}:schema '
                    f'xmlns:{prefix}="{XSD_NAMESPACE}"'
                    f"{attributes}>"
                ),
                body,
                f"</{prefix}:schema>",
                "",
            ]
        ),
        encoding="utf-8",
    )


@pytest.fixture
def utility_root() -> Path:
    """Return the xsd-extraction utility directory containing the tests."""
    return Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("prefix", ["xsd", "xs"])
def test_accepts_supported_schema_prefixes(
    tmp_path: Path,
    utility_root: Path,
    prefix: str,
) -> None:
    input_file = tmp_path / f"{prefix}-schema.xsd"
    output_file = tmp_path / f"{prefix}-schema.txt"

    write_schema(
        input_file,
        prefix=prefix,
        body=f'<{prefix}:element name="MESSAGE" type="{prefix}:string"/>',
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)
    assert output_file.is_file()


@pytest.mark.parametrize(
    ("declaration", "description"),
    [
        ('<?xml version="1.1" encoding="UTF-8"?>', "different XML version"),
        ('<?xml version="1.0" encoding="utf-8"?>', "different encoding case"),
        ('<?xml version="1.0" encoding="UTF-16"?>', "different encoding"),
        (f" {XML_DECLARATION}", "leading whitespace"),
        (f"{XML_DECLARATION} ", "trailing whitespace"),
        ("", "missing declaration"),
    ],
)
def test_rejects_any_line_one_that_is_not_exact(
    tmp_path: Path,
    utility_root: Path,
    declaration: str,
    description: str,
) -> None:
    input_file = tmp_path / "invalid-line-one.xsd"
    output_file = tmp_path / "output.txt"

    write_schema(input_file, declaration=declaration)

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode != 0, description
    assert not output_file.exists()
    assert input_file.name in combined_output(result)


@pytest.mark.parametrize(
    "line_two",
    [
        '<schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
        '<foo:schema xmlns:foo="http://www.w3.org/2001/XMLSchema">',
        '<xsd:element xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
    ],
)
def test_rejects_line_two_that_does_not_begin_with_supported_schema_name(
    tmp_path: Path,
    utility_root: Path,
    line_two: str,
) -> None:
    input_file = tmp_path / "wrong-root.xsd"
    output_file = tmp_path / "output.txt"
    input_file.write_text(
        f"{XML_DECLARATION}\n{line_two}\n",
        encoding="utf-8",
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode != 0
    assert not output_file.exists()
    assert input_file.name in combined_output(result)


def test_rejects_missing_xml_schema_namespace_binding(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "missing-binding.xsd"
    output_file = tmp_path / "output.txt"
    input_file.write_text(
        "\n".join(
            [
                XML_DECLARATION,
                '<xsd:schema xmlns:xsd="https://example.com/not-xsd">',
                "</xsd:schema>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode != 0
    assert not output_file.exists()
    assert input_file.name in combined_output(result)


@pytest.mark.parametrize(
    "line_two",
    [
        f'<xsd:schema xmlns:xs="{XSD_NAMESPACE}">',
        f'<xs:schema xmlns:xsd="{XSD_NAMESPACE}">',
    ],
)
def test_rejects_schema_prefix_namespace_binding_mismatch(
    tmp_path: Path,
    utility_root: Path,
    line_two: str,
) -> None:
    input_file = tmp_path / "prefix-mismatch.xsd"
    output_file = tmp_path / "output.txt"
    input_file.write_text(
        f"{XML_DECLARATION}\n{line_two}\n",
        encoding="utf-8",
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode != 0
    assert not output_file.exists()
    assert input_file.name in combined_output(result)


def test_rejects_ambiguous_schema_prefix_declarations(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "ambiguous-prefix.xsd"
    output_file = tmp_path / "output.txt"
    input_file.write_text(
        "\n".join(
            [
                XML_DECLARATION,
                (
                    f'<xsd:schema xmlns:xsd="{XSD_NAMESPACE}" '
                    f'xmlns:xs="{XSD_NAMESPACE}">'
                ),
                "</xsd:schema>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode != 0
    assert not output_file.exists()
    assert input_file.name in combined_output(result)


def test_reports_nonexistent_input_path(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    missing_path = tmp_path / "does-not-exist.xsd"
    output_file = tmp_path / "output.txt"

    result = run_cli(
        "--input-path",
        str(missing_path),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode != 0
    assert str(missing_path) in combined_output(result)
    assert not output_file.exists()


def test_writes_every_schema_attribute_to_single_file_output(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "attributes.xsd"
    output_file = tmp_path / "attributes.txt"

    write_schema(
        input_file,
        schema_attributes=(
            'xmlns:uad="https://example.com/uad" '
            'targetNamespace="https://example.com/uad" '
            'elementFormDefault="qualified" '
            'attributeFormDefault="unqualified" '
            'version="3.6.0"'
        ),
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)
    output = output_file.read_text(encoding="utf-8")

    expected_fragments = [
        f'xmlns:xsd="{XSD_NAMESPACE}"',
        'xmlns:uad="https://example.com/uad"',
        'targetNamespace="https://example.com/uad"',
        'elementFormDefault="qualified"',
        'attributeFormDefault="unqualified"',
        'version="3.6.0"',
    ]
    for fragment in expected_fragments:
        assert fragment in output


def test_writes_each_unique_xsd_artifact(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "artifacts.xsd"
    output_file = tmp_path / "artifacts.txt"

    write_schema(
        input_file,
        body="\n".join(
            [
                '<xsd:annotation><xsd:documentation>Example</xsd:documentation></xsd:annotation>',
                '<xsd:import namespace="https://example.com/common"/>',
                '<xsd:complexType name="MessageType">',
                "  <xsd:sequence>",
                '    <xsd:element name="MESSAGE" type="xsd:string"/>',
                "  </xsd:sequence>",
                "</xsd:complexType>",
                '<xsd:simpleType name="CodeType">',
                '  <xsd:restriction base="xsd:string">',
                '    <xsd:enumeration value="A"/>',
                "  </xsd:restriction>",
                "</xsd:simpleType>",
            ]
        ),
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)
    output = output_file.read_text(encoding="utf-8")

    expected_artifacts = {
        "annotation",
        "documentation",
        "import",
        "complexType",
        "sequence",
        "element",
        "simpleType",
        "restriction",
        "enumeration",
    }
    for artifact in expected_artifacts:
        assert artifact in output


def test_does_not_repeat_duplicate_artifact_names(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "duplicates.xsd"
    output_file = tmp_path / "duplicates.txt"

    write_schema(
        input_file,
        body="\n".join(
            [
                '<xsd:element name="First" type="xsd:string"/>',
                '<xsd:element name="Second" type="xsd:string"/>',
                '<xsd:element name="Third" type="xsd:string"/>',
            ]
        ),
    )

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)
    output_lines = [
        line.strip()
        for line in output_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    artifact_lines = [
        line
        for line in output_lines
        if line == "element" or line.endswith(":element")
    ]
    assert len(artifact_lines) == 1


def test_folder_input_creates_one_output_file_per_input_file(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_folder = tmp_path / "schemas"
    output_folder = tmp_path / "extracted"
    input_folder.mkdir()

    write_schema(
        input_folder / "alpha.xsd",
        body='<xsd:element name="Alpha" type="xsd:string"/>',
    )
    write_schema(
        input_folder / "beta.xsd",
        prefix="xs",
        body='<xs:complexType name="BetaType"/>',
    )

    result = run_cli(
        "--input-path",
        str(input_folder),
        "--output-path",
        str(output_folder),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)
    assert output_folder.is_dir()

    output_files = sorted(path for path in output_folder.iterdir() if path.is_file())
    assert len(output_files) == 2

    combined_contents = "\n".join(
        path.read_text(encoding="utf-8") for path in output_files
    )
    assert "element" in combined_contents
    assert "complexType" in combined_contents


def test_folder_processing_does_not_merge_source_files(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_folder = tmp_path / "schemas"
    output_folder = tmp_path / "extracted"
    input_folder.mkdir()

    write_schema(
        input_folder / "one.xsd",
        schema_attributes='targetNamespace="https://example.com/one"',
        body='<xsd:element name="One" type="xsd:string"/>',
    )
    write_schema(
        input_folder / "two.xsd",
        schema_attributes='targetNamespace="https://example.com/two"',
        body='<xsd:attribute name="Two" type="xsd:string"/>',
    )

    result = run_cli(
        "--input-path",
        str(input_folder),
        "--output-path",
        str(output_folder),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)

    outputs = [
        path.read_text(encoding="utf-8")
        for path in output_folder.iterdir()
        if path.is_file()
    ]
    assert len(outputs) == 2
    assert any("https://example.com/one" in output for output in outputs)
    assert any("https://example.com/two" in output for output in outputs)
    assert not any(
        "https://example.com/one" in output
        and "https://example.com/two" in output
        for output in outputs
    )


def test_folder_error_identifies_the_invalid_file(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_folder = tmp_path / "schemas"
    output_folder = tmp_path / "extracted"
    input_folder.mkdir()

    write_schema(input_folder / "valid.xsd")
    invalid_file = input_folder / "invalid.xsd"
    write_schema(
        invalid_file,
        declaration='<?xml version="1.0" encoding="UTF-16"?>',
    )

    result = run_cli(
        "--input-path",
        str(input_folder),
        "--output-path",
        str(output_folder),
        cwd=utility_root,
    )

    assert result.returncode != 0
    assert invalid_file.name in combined_output(result)


def test_same_input_produces_identical_output(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "deterministic.xsd"
    first_output = tmp_path / "first.txt"
    second_output = tmp_path / "second.txt"

    write_schema(
        input_file,
        schema_attributes=(
            'targetNamespace="https://example.com/deterministic" '
            'elementFormDefault="qualified"'
        ),
        body="\n".join(
            [
                '<xsd:complexType name="ExampleType">',
                "  <xsd:sequence>",
                '    <xsd:element name="Value" type="xsd:string"/>',
                "  </xsd:sequence>",
                "</xsd:complexType>",
            ]
        ),
    )

    first_result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(first_output),
        cwd=utility_root,
    )
    second_result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(second_output),
        cwd=utility_root,
    )

    assert first_result.returncode == 0, combined_output(first_result)
    assert second_result.returncode == 0, combined_output(second_result)
    assert first_output.read_bytes() == second_output.read_bytes()


def test_source_file_is_not_modified(
    tmp_path: Path,
    utility_root: Path,
) -> None:
    input_file = tmp_path / "source.xsd"
    output_file = tmp_path / "output.txt"

    write_schema(
        input_file,
        body='<xsd:element name="MESSAGE" type="xsd:string"/>',
    )
    original_bytes = input_file.read_bytes()

    result = run_cli(
        "--input-path",
        str(input_file),
        "--output-path",
        str(output_file),
        cwd=utility_root,
    )

    assert result.returncode == 0, combined_output(result)
    assert input_file.read_bytes() == original_bytes
