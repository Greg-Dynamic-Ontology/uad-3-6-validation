"""Run the extracted required-data suite against this repository."""
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "data" / "uad36-test-suite" / "tests"
FIXTURES = TESTS / "fixtures" / "required_data"


class RepositoryPaths:
    """Bind the extracted tests to the actual application and schema root."""

    def pytest_collection_modifyitems(self, items):
        for item in items:
            module = item.module
            source = Path(module.__file__).resolve()

            if source.parent != TESTS.resolve():
                continue

            if source.name == "test_required_data_fixtures.py":
                module.ROOT = ROOT
                module.FIXTURES = FIXTURES
            elif source.name == "test_required_data_acceptance.py":
                module.FIXTURES = FIXTURES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        choices=("all", "fixtures", "acceptance"),
        default="all",
    )
    args = parser.parse_args()

    required = [
        ROOT / "app",
        ROOT / "specs",
        FIXTURES / "manifest.csv",
        FIXTURES / "baseline" / "SF1_Appraisal_v1.4.xml",
        FIXTURES / "tests",
    ]
    for path in required:
        if not path.exists():
            parser.error(f"Required path not found: {path}")

    filenames = {
        "fixtures": "test_required_data_fixtures.py",
        "acceptance": "test_required_data_acceptance.py",
    }
    selected = (
        list(filenames.values())
        if args.suite == "all"
        else [filenames[args.suite]]
    )
    for filename in selected:
        if not (TESTS / filename).is_file():
            parser.error(f"Test file not found: {TESTS / filename}")

    sys.path.insert(0, str(ROOT))

    try:
        import pytest
    except ImportError:
        parser.error("pytest is missing from the selected Python environment.")

    return pytest.main(
        [
            *(str(TESTS / filename) for filename in selected),
            f"--rootdir={ROOT}",
            "-q",
            "--tb=short",
        ],
        plugins=[RepositoryPaths()],
    )


if __name__ == "__main__":
    raise SystemExit(main())