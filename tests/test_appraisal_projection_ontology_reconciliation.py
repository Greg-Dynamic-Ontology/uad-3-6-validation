"""Acceptance test for IT-7R6S2 appraisal-to-ontology reconciliation."""

from inspect import signature
from pathlib import Path

import app
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL

from app.projections.logical_schema_to_ontology import (
    project_logical_schema_to_ontology,
)
from app.services.rdf_projection import (
    INSTANCE_NAMESPACE,
    RdfProjector,
)
from app.services.schema_loader import SchemaLoader


PROJECT_ROOT = Path(app.__file__).resolve().parents[1]
UAD_SCHEMA_FILE = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)
SAMPLE_APPRAISAL = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "Appendix D-1 URAR Sample Use Cases and XML Files"
    / "Appendix D-1 SF1_Appraisal"
    / "SF1_Appraisal_v1.4.xml"
)

UAD_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/schema#"
)
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

DOCUMENTED_EXTERNAL_NAMESPACES = (
    "http://www.w3.org/1999/xlink",
    "http://www.w3.org/2001/XMLSchema-instance",
)


def _is_external(term: URIRef) -> bool:
    """Return whether a term belongs to a documented external vocabulary."""

    return any(
        str(term).startswith(namespace)
        for namespace in DOCUMENTED_EXTERNAL_NAMESPACES
    )


def _instance_subject(term: object) -> bool:
    """Return whether a term identifies an appraisal instance resource."""

    return isinstance(term, URIRef) and str(term).startswith(
        INSTANCE_NAMESPACE
    )


def _declared_class(ontology: Graph, term: URIRef) -> bool:
    """Return whether the ontology declares an RDF/OWL class."""

    return (
        (term, RDF.type, OWL.Class) in ontology
        or (term, RDF.type, RDFS.Class) in ontology
    )


def _declared_property(ontology: Graph, term: URIRef) -> bool:
    """Return whether the ontology declares an RDF/OWL property."""

    return any(
        (term, RDF.type, property_type) in ontology
        for property_type in (
            RDF.Property,
            OWL.DatatypeProperty,
            OWL.ObjectProperty,
        )
    )


def test_projected_appraisal_terms_reconcile_with_mismo_ontology() -> None:
    """IT-7R6S2: Use governed ontology terms or visible dispositions."""

    constructor_parameters = signature(RdfProjector).parameters
    assert "ontology" in constructor_parameters, (
        "RdfProjector must accept the governed MISMO ontology so XML "
        "names can be resolved to declared RDF terms."
    )

    assert UAD_SCHEMA_FILE.is_file()
    assert SAMPLE_APPRAISAL.is_file()

    logical_model = SchemaLoader().load(UAD_SCHEMA_FILE)
    ontology = project_logical_schema_to_ontology(logical_model)
    assert len(ontology) > 0

    projector = RdfProjector(ontology=ontology)
    instance_graph = projector.project(
        xml_bytes=SAMPLE_APPRAISAL.read_bytes(),
        source_name=SAMPLE_APPRAISAL.name,
    )
    assert len(instance_graph) > 0

    instance_classes = {
        class_iri
        for subject, _, class_iri in instance_graph.triples(
            (None, RDF.type, None)
        )
        if _instance_subject(subject)
        and isinstance(class_iri, URIRef)
    }
    assert instance_classes

    undeclared_classes = {
        class_iri
        for class_iri in instance_classes
        if not _declared_class(ontology, class_iri)
        and not _is_external(class_iri)
    }
    assert not undeclared_classes, (
        "Appraisal classes are not declared by the governed MISMO "
        f"ontology: {sorted(map(str, undeclared_classes))[:10]}"
    )

    instance_properties = {
        predicate
        for subject, predicate, _ in instance_graph
        if _instance_subject(subject) and predicate != RDF.type
    }
    assert instance_properties

    undeclared_properties = {
        predicate
        for predicate in instance_properties
        if not _declared_property(ontology, predicate)
        and not _is_external(predicate)
    }
    assert not undeclared_properties, (
        "Appraisal properties are not declared by the governed MISMO "
        f"ontology: {sorted(map(str, undeclared_properties))[:10]}"
    )

    for subject, predicate, value in instance_graph:
        if not _instance_subject(subject) or not isinstance(value, Literal):
            continue
        if _is_external(predicate):
            continue
        if (predicate, RDF.type, OWL.DatatypeProperty) not in ontology:
            continue

        ranges = tuple(ontology.objects(predicate, RDFS.range))
        assert len(ranges) == 1, (
            f"Datatype property {predicate} must have one governed range."
        )
        expected_datatype = ranges[0]
        assert isinstance(expected_datatype, URIRef)
        assert (
            str(expected_datatype).startswith(str(XSD))
            or (
                expected_datatype,
                RDF.type,
                RDFS.Datatype,
            ) in ontology
        )
        assert value.datatype == expected_datatype, (
            f"Value {value!r} for {predicate} does not use its governed "
            f"datatype {expected_datatype}."
        )

    controlled_properties = {
        property_iri
        for property_iri in ontology.subjects(
            RDFS.range,
            SKOS.Concept,
        )
        if isinstance(property_iri, URIRef)
    }
    assert controlled_properties, (
        "The complete UAD subset must identify its controlled-vocabulary "
        "properties in the governed MISMO ontology."
    )

    for subject, predicate, value in instance_graph:
        if predicate not in controlled_properties:
            continue
        assert isinstance(value, URIRef)
        assert (value, RDF.type, SKOS.Concept) in ontology
        assert any(ontology.objects(value, SKOS.inScheme))

    unresolved_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<MESSAGE xmlns="http://www.mismo.org/residential/2009/schemas"
         xmlns:unknown="urn:dynamicontology:test:unknown">
  <unknown:UNMAPPED_TERM>visible</unknown:UNMAPPED_TERM>
</MESSAGE>
""".encode("utf-8")
    unresolved_graph = projector.project(
        xml_bytes=unresolved_xml,
        source_name="unresolved.xml",
    )

    unresolved_dispositions = {
        resource
        for resource in unresolved_graph.subjects(
            RDF.type,
            UAD_SCHEMA.InstanceProjectionDisposition,
        )
        if (
            resource,
            UAD_SCHEMA.projectionAction,
            Literal("unresolved"),
        ) in unresolved_graph
        and (
            resource,
            UAD_SCHEMA.sourceQName,
            Literal("{urn:dynamicontology:test:unknown}UNMAPPED_TERM"),
        ) in unresolved_graph
    }
    assert len(unresolved_dispositions) == 1
