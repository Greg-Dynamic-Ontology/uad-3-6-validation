"""
Extraction logic for the XSD Extraction utility.

This module:

1. Verifies that the input path exists.
2. Distinguishes between file and folder input.
3. Filters folder input to XSD files only.
4. Validates the required XML declaration on line 1.
5. Skips blank lines and XML comments after the XML declaration.
6. Locates and validates the opening schema element.
7. Captures every attribute on the opening schema element.
8. Parses the XSD as XML.
9. Collects every unique XSD component type used in the file.
10. Writes one deterministic text output file per input XSD.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


REQUIRED_XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"

SCHEMA_PREFIX_PATTERN = re.compile(
    r"^<(xsd|xs):schema\b"
)

NAMESPACE_DECLARATION_PATTERN = re.compile(
    r"""xmlns:(xsd|xs)\s*=\s*["']([^"']+)["']"""
)

ATTRIBUTE_PATTERN = re.compile(
    r"""
    (?P<name>[A-Za-z_][A-Za-z0-9_.:-]*)
    \s*=\s*
    (?P<quote>["'])
    (?P<value>.*?)
    (?P=quote)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class SchemaHeader:
    """
    Information extracted from the opening schema element.
    """

    line_number: int
    schema_prefix: str
    schema_line: str
    attributes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ExtractionResult:
    """
    Information extracted from one XSD file.
    """

    source_path: Path
    schema_header: SchemaHeader
    component_names: tuple[str, ...]


def process(input_path: Path, output_path: Path) -> int:
    """
    Extract one XSD file or every XSD file in a folder.

    Args:
        input_path:
            Path to one XSD file or a folder containing XSD files.

        output_path:
            Output file for one input file, or output folder when
            the input path is a folder.

    Returns:
        0 when all input files are extracted successfully.

        1 when an input path, XSD file, or output path causes an error.
    """

    if not input_path.exists():
        print(f"ERROR: Input path does not exist: {input_path}")
        return 1

    if input_path.is_file():
        return process_single_file(
            input_path=input_path,
            output_path=output_path,
        )

    if input_path.is_dir():
        return process_folder(
            input_path=input_path,
            output_path=output_path,
        )

    print(
        "ERROR: Input path is neither a regular file nor a folder: "
        f"{input_path}"
    )
    return 1


def process_single_file(
    input_path: Path,
    output_path: Path,
) -> int:
    """
    Extract one XSD file into one output file.
    """

    if input_path.suffix.lower() != ".xsd":
        print(f"ERROR: Input file is not an XSD file: {input_path}")
        return 1

    print()
    print("Processing input file:")
    print(f"  {input_path}")
    print()

    result = extract_xsd_file(input_path)

    if result is None:
        return 1

    if not write_output_file(
        result=result,
        output_path=output_path,
    ):
        return 1

    print()
    print("Extraction complete.")
    return 0


def process_folder(
    input_path: Path,
    output_path: Path,
) -> int:
    """
    Extract every XSD file directly contained in a folder.
    """

    xsd_files = find_xsd_files(input_path)

    if not xsd_files:
        print(f"ERROR: Input folder contains no XSD files: {input_path}")
        return 1

    print()
    print("Processing input folder:")
    print(f"  {input_path}")
    print()
    print(f"Found {len(xsd_files)} XSD file(s):")

    for path in xsd_files:
        print(f"  {path.name}")

    try:
        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as error:
        print()
        print("ERROR:")
        print(f"Unable to create output folder: {output_path}")
        print(error)
        return 1

    print()

    for input_file in xsd_files:
        result = extract_xsd_file(input_file)

        if result is None:
            return 1

        destination = output_path / f"{input_file.stem}.txt"

        if not write_output_file(
            result=result,
            output_path=destination,
        ):
            return 1

    print()
    print(
        f"Extraction complete: {len(xsd_files)} output file(s) written."
    )

    return 0


def find_xsd_files(input_path: Path) -> list[Path]:
    """
    Return XSD files directly contained in a folder.

    Files are returned in deterministic filename order.
    """

    return sorted(
        (
            path
            for path in input_path.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".xsd"
        ),
        key=lambda path: path.name.lower(),
    )


def extract_xsd_file(
    path: Path,
) -> ExtractionResult | None:
    """
    Validate and extract information from one XSD file.
    """

    print(f"Processing {path.name}")

    lines = read_file_lines(path)

    if lines is None:
        return None

    if not lines:
        print_error(
            path=path,
            message="The file is empty.",
        )
        return None

    xml_declaration = remove_line_ending(lines[0])

    if not validate_xml_declaration(
        path=path,
        xml_declaration=xml_declaration,
    ):
        return None

    print("  XML declaration: PASS")

    schema_header = find_and_validate_schema_header(
        path=path,
        lines=lines,
    )

    if schema_header is None:
        return None

    print(
        "  Schema declaration on line "
        f"{schema_header.line_number}: PASS"
    )

    component_names = extract_component_names(path)

    if component_names is None:
        return None

    print(
        f"  Schema attributes found: "
        f"{len(schema_header.attributes)}"
    )
    print(
        f"  Unique XSD components found: "
        f"{len(component_names)}"
    )

    return ExtractionResult(
        source_path=path,
        schema_header=schema_header,
        component_names=component_names,
    )


def read_file_lines(
    path: Path,
) -> list[str] | None:
    """
    Read all lines from one UTF-8 input file.
    """

    try:
        with path.open(
            mode="r",
            encoding="utf-8",
            newline="",
        ) as input_file:
            return input_file.readlines()
    except (OSError, UnicodeError) as error:
        print_error(
            path=path,
            message=f"Unable to read file: {error}",
        )
        return None


def validate_xml_declaration(
    path: Path,
    xml_declaration: str,
) -> bool:
    """
    Validate the exact XML declaration required on line 1.
    """

    if xml_declaration == REQUIRED_XML_DECLARATION:
        return True

    print()
    print("ERROR:")
    print(f"File: {path}")
    print()
    print("Line 1 must be exactly:")
    print(REQUIRED_XML_DECLARATION)
    print()
    print("Found:")
    print(repr(xml_declaration))

    return False


def find_and_validate_schema_header(
    path: Path,
    lines: list[str],
) -> SchemaHeader | None:
    """
    Locate and validate the opening schema element.

    Blank lines and XML comments following the XML declaration are
    skipped. Both single-line and multi-line comments are supported.
    """

    schema_result = find_schema_line(
        path=path,
        lines=lines,
    )

    if schema_result is None:
        return None

    line_number, schema_line = schema_result

    schema_match = SCHEMA_PREFIX_PATTERN.match(schema_line)

    if schema_match is None:
        print()
        print("ERROR:")
        print(f"File: {path}")
        print()
        print(
            f"Line {line_number} must begin with "
            "'<xsd:schema' or '<xs:schema'."
        )
        print()
        print("Found:")
        print(repr(schema_line))

        return None

    schema_prefix = schema_match.group(1)

    namespace_declarations = (
        NAMESPACE_DECLARATION_PATTERN.findall(schema_line)
    )

    matching_prefixes = [
        prefix
        for prefix, namespace in namespace_declarations
        if namespace == XML_SCHEMA_NAMESPACE
    ]

    if not matching_prefixes:
        print_error(
            path=path,
            message=(
                "The opening schema element must declare the XML "
                "Schema namespace using 'xmlns:xsd' or 'xmlns:xs'."
            ),
        )
        return None

    if len(matching_prefixes) > 1:
        print_error(
            path=path,
            message=(
                "Both 'xmlns:xsd' and 'xmlns:xs' declare the XML "
                "Schema namespace. The schema prefix is ambiguous."
            ),
        )
        return None

    namespace_prefix = matching_prefixes[0]

    if namespace_prefix != schema_prefix:
        print()
        print("ERROR:")
        print(f"File: {path}")
        print()
        print(
            "The schema element prefix does not match the prefix "
            "bound to the XML Schema namespace."
        )
        print()
        print(f"Schema element prefix: {schema_prefix}")
        print(f"Namespace prefix:      {namespace_prefix}")

        return None

    attributes = extract_schema_attributes(schema_line)

    return SchemaHeader(
        line_number=line_number,
        schema_prefix=schema_prefix,
        schema_line=schema_line,
        attributes=attributes,
    )


def find_schema_line(
    path: Path,
    lines: list[str],
) -> tuple[int, str] | None:
    """
    Find the first substantive line following the XML declaration.

    Blank lines and XML comments are skipped.
    """

    inside_comment = False

    for line_number, raw_line in enumerate(
        lines[1:],
        start=2,
    ):
        line = remove_line_ending(raw_line)
        remaining = line.strip()

        while remaining:
            if inside_comment:
                comment_end = remaining.find("-->")

                if comment_end == -1:
                    remaining = ""
                    continue

                inside_comment = False
                remaining = remaining[
                    comment_end + len("-->") :
                ].strip()
                continue

            if remaining.startswith("<!--"):
                comment_end = remaining.find(
                    "-->",
                    len("<!--"),
                )

                if comment_end == -1:
                    inside_comment = True
                    remaining = ""
                    continue

                remaining = remaining[
                    comment_end + len("-->") :
                ].strip()
                continue

            return line_number, remaining

    if inside_comment:
        print_error(
            path=path,
            message="An XML comment was opened but not closed.",
        )
        return None

    print_error(
        path=path,
        message=(
            "No opening '<xsd:schema' or '<xs:schema' element "
            "was found after the XML declaration."
        ),
    )
    return None


def extract_schema_attributes(
    schema_line: str,
) -> tuple[tuple[str, str], ...]:
    """
    Extract every attribute from the opening schema element.

    Attribute order is preserved as it appears in the source file.
    """

    return tuple(
        (
            match.group("name"),
            match.group("value"),
        )
        for match in ATTRIBUTE_PATTERN.finditer(schema_line)
    )


def extract_component_names(
    path: Path,
) -> tuple[str, ...] | None:
    """
    Return every unique XML Schema component type used in one file.

    The opening schema element itself is excluded. Only elements in
    the XML Schema namespace are included.
    """

    try:
        document = ElementTree.parse(path)
    except ElementTree.ParseError as error:
        print_error(
            path=path,
            message=f"Unable to parse XML: {error}",
        )
        return None
    except OSError as error:
        print_error(
            path=path,
            message=f"Unable to read XML: {error}",
        )
        return None

    root = document.getroot()

    expected_root_tag = (
        f"{{{XML_SCHEMA_NAMESPACE}}}schema"
    )

    if root.tag != expected_root_tag:
        print_error(
            path=path,
            message=(
                "The document root is not an XML Schema "
                "'schema' element."
            ),
        )
        return None

    namespace_prefix = (
        f"{{{XML_SCHEMA_NAMESPACE}}}"
    )

    component_names: set[str] = set()

    for element in root.iter():
        if element is root:
            continue

        if not isinstance(element.tag, str):
            continue

        if not element.tag.startswith(namespace_prefix):
            continue

        local_name = element.tag[
            len(namespace_prefix) :
        ]

        component_names.add(local_name)

    return tuple(
        sorted(
            component_names,
            key=str.lower,
        )
    )


def write_output_file(
    result: ExtractionResult,
    output_path: Path,
) -> bool:
    """
    Write one deterministic text output file.
    """

    output_lines = [
        f"Source file: {result.source_path.name}",
        (
            "Schema declaration line: "
            f"{result.schema_header.line_number}"
        ),
        (
            "Schema prefix: "
            f"{result.schema_header.schema_prefix}"
        ),
        "",
        "Schema attributes:",
    ]

    if result.schema_header.attributes:
        for name, value in result.schema_header.attributes:
            output_lines.append(
                f"  {name} = {value}"
            )
    else:
        output_lines.append("  None")

    output_lines.extend(
        [
            "",
            "Unique XSD components:",
        ]
    )

    if result.component_names:
        for component_name in result.component_names:
            output_lines.append(
                f"  {component_name}"
            )
    else:
        output_lines.append("  None")

    output_lines.append("")

    try:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            "\n".join(output_lines),
            encoding="utf-8",
        )
    except OSError as error:
        print()
        print("ERROR:")
        print(f"Output file: {output_path}")
        print(f"Unable to write output file: {error}")
        return False

    print(f"  Wrote: {output_path}")

    return True


def remove_line_ending(
    value: str,
) -> str:
    """
    Remove one line ending without removing other whitespace.
    """

    if value.endswith("\r\n"):
        return value[:-2]

    if value.endswith("\n") or value.endswith("\r"):
        return value[:-1]

    return value


def print_error(
    path: Path,
    message: str,
) -> None:
    """
    Print a consistently formatted input-file error.
    """

    print()
    print("ERROR:")
    print(f"File: {path}")
    print(message)