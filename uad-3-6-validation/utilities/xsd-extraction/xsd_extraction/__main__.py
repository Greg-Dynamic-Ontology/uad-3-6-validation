"""
Entry point for the XSD Extraction utility.

This module enables the utility to be executed with:

    python -m xsd_extraction

All command-line processing is delegated to cli.py.
"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())