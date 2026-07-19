"""
Command-line interface for the XSD Extraction utility.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from .extractor import process


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="xsd_extraction",
        description=(
            "Extract schema attributes and unique XSD artifacts "
            "from an XSD file or folder."
        ),
    )

    parser.add_argument(
        "--input-path",
        required=True,
        type=Path,
        help="Path to one XSD file or a folder containing XSD files.",
    )

    parser.add_argument(
        "--output-path",
        required=True,
        type=Path,
        help=(
            "Output file for one input file, or output folder "
            "when the input path is a folder."
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()

    args = parser.parse_args(argv)

    print("XSD Extraction Utility")

    return process(
        input_path=args.input_path,
        output_path=args.output_path,
    )