"""Minimal XML checks performed before schema candidate ingestion."""

from lxml import etree


EXPECTED_SCHEMA_ROOT = "{http://www.w3.org/2001/XMLSchema}schema"


class MalformedSchemaXmlError(ValueError):
    """The submitted schema text is not a well-formed XML document."""


class IncorrectSchemaRootError(ValueError):
    """Well-formed submitted XML has an incorrect schema document root."""

    def __init__(self, *, root_name: str, namespace: str) -> None:
        self.root_name = root_name
        self.namespace = namespace
        super().__init__(
            f"Expected XML Schema root {EXPECTED_SCHEMA_ROOT}; "
            f"received local name {root_name!r} in namespace {namespace!r}."
        )

    @property
    def detail(self) -> dict[str, str]:
        return {
            "message": str(self),
            "expected_root": EXPECTED_SCHEMA_ROOT,
            "actual_root_name": self.root_name,
            "actual_root_namespace": self.namespace,
        }


def _parse_xml(raw_text: str) -> etree._Element:
    """Parse one document without entity expansion or external resource access."""
    parser = etree.XMLParser(
        recover=False,
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
    )
    try:
        return etree.fromstring(raw_text.encode("utf-8"), parser=parser)
    except (etree.XMLSyntaxError, UnicodeError) as error:
        raise MalformedSchemaXmlError(
            f"Malformed XML in proposed schema: {error}"
        ) from error


def check_schema_xml_well_formed(raw_text: str) -> None:
    """Check XML syntax alone, without classifying the document root."""
    _parse_xml(raw_text)


def check_schema_candidate_xml(raw_text: str) -> None:
    """Require well-formed XML with the XML Schema vocabulary's schema root.

    Namespace prefixes and target namespaces do not affect this decision.
    Imports/includes are not resolved, and component analysis is not started.
    Passing this gate is not certification of XML Schema correctness.
    """
    root = _parse_xml(raw_text)
    if root.tag != EXPECTED_SCHEMA_ROOT:
        name = etree.QName(root)
        raise IncorrectSchemaRootError(
            root_name=name.localname,
            namespace=name.namespace or "",
        )
