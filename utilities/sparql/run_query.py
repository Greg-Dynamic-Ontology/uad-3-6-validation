"""Run a SPARQL query file against a local RDF document.

SELECT results are printed as CSV with column headings. ASK prints true/false.
CONSTRUCT and DESCRIBE results are printed as Turtle. Input files are read only.
Requires the project's existing rdflib dependency.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rdflib import Graph


def _existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute a SPARQL query against a local RDF file without modifying it.",
    )
    parser.add_argument("--data", required=True, type=_existing_file, help="RDF data file.")
    parser.add_argument("--query", required=True, type=_existing_file, help="SPARQL query (.rq) file.")
    parser.add_argument(
        "--rdf-format", default=None,
        help="RDFLib input format, such as turtle or xml; inferred from the filename when omitted.",
    )
    args = parser.parse_args(argv)

    try:
        graph = Graph().parse(location=str(args.data), format=args.rdf_format)
        query = args.query.read_text(encoding="utf-8-sig")
        result = graph.query(query)
        if result.type == "SELECT":
            output = result.serialize(format="csv")
        elif result.type == "ASK":
            output = "true\n" if result.askAnswer else "false\n"
        elif result.type in ("CONSTRUCT", "DESCRIBE"):
            if result.graph is None:
                raise ValueError("The query returned no RDF result graph.")
            output = result.graph.serialize(format="turtle")
        else:
            raise ValueError(f"Unsupported query result type: {result.type}")
    except Exception as error:
        print(f"SPARQL query failed: {error}", file=sys.stderr)
        return 1

    # UTF-8 output also supports redirection to a CSV or Turtle result file.
    encoded = output if isinstance(output, bytes) else output.encode("utf-8")
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    else:
        sys.stdout.write(encoded.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
