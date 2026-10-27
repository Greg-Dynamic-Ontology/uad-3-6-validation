"""IT-62R1S1: accept configuration classes/properties defined by RDF vocabulary.

Proposed production contract:
app.services.configuration_knowledge.validate_configuration_vocabulary(
    configuration_graph=Graph, vocabulary_graph=Graph,
) returns a result with conforms: bool, undefined_classes: tuple[URIRef, ...],
and undefined_properties: tuple[URIRef, ...]. This operation checks vocabulary
coverage; later rules govern active-source selection and workbook requirements.

Definitions may use RDFS classes/RDF properties or OWL class/property types.
Configuration individuals in the cfg namespace are not themselves class or
property uses. Dynamically named extension terms ensure the supplied vocabulary,
not a built-in whitelist of known names, determines whether terms are defined.
"""

from importlib import import_module, util
from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS
from rdflib.compare import isomorphic
from rdflib.namespace import OWL

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
MODULE = "app.services.configuration_knowledge"


def _validator():
    specification = util.find_spec(MODULE)
    assert specification is not None, (
        "IT-62R1S1 requires app.services.configuration_knowledge to validate "
        "configuration RDF classes and properties against an explicit RDF vocabulary."
    )
    operation = getattr(import_module(MODULE), "validate_configuration_vocabulary", None)
    assert callable(operation), (
        "IT-62R1S1 requires validate_configuration_vocabulary("
        "configuration_graph=..., vocabulary_graph=...) with an explicit validation result."
    )
    return operation


def _copy(graph):
    copy = Graph()
    for triple in graph:
        copy.add(triple)
    return copy


@pytest.mark.parametrize("definition_style", ["rdfs", "owl"], ids=["rdfs-rdf-definitions", "owl-definitions"])
def test_it_62_r1_s1_accepts_configuration_with_defined_classes_and_properties(
    tmp_path: Path, definition_style: str,
) -> None:
    token = uuid4().hex
    application = CFG[f"application-{token}"]
    collection = CFG[f"workbooks-{token}"]
    workbook = CFG[f"workbook-{token}"]
    experience = CFG[f"experience-{token}"]
    extension_class = CFG[f"OperatorProfile-{token}"]
    extension_property = CFG[f"usesOperatorProfile-{token}"]
    operator_profile = BNode()
    classes = (
        CFG.ApplicationConfiguration, CFG.GovernedSourceWorkbookCollection,
        CFG.GovernedSourceArtifact, CFG.UserExperienceProfile, extension_class,
    )
    object_properties = (
        CFG.hasSourceWorkbooks, CFG.containsWorkbook, CFG.activeComplianceSource,
        CFG.usesExperience, extension_property,
    )
    datatype_properties = (
        CFG.sourceFileLocation, CFG.ruleDataSheetName, CFG.showsDeveloperDiagnostics,
    )
    vocabulary = Graph()
    vocabulary.bind("cfg", CFG)
    for term in classes:
        vocabulary.add((term, RDF.type, RDFS.Class if definition_style == "rdfs" else OWL.Class))
        vocabulary.add((term, RDFS.label, Literal(f"Defined class {term}")))
    for term in object_properties:
        vocabulary.add((term, RDF.type, RDF.Property if definition_style == "rdfs" else OWL.ObjectProperty))
    for term in datatype_properties:
        vocabulary.add((term, RDF.type, RDF.Property if definition_style == "rdfs" else OWL.DatatypeProperty))
    configuration = Graph()
    configuration.bind("cfg", CFG)
    for triple in (
        (application, RDF.type, CFG.ApplicationConfiguration),
        (application, RDFS.label, Literal("Configuration with explicitly defined vocabulary")),
        (application, CFG.hasSourceWorkbooks, collection),
        (application, CFG.activeComplianceSource, workbook),
        (application, CFG.usesExperience, experience),
        (application, extension_property, operator_profile),
        (collection, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (collection, CFG.containsWorkbook, workbook),
        (workbook, RDF.type, CFG.GovernedSourceArtifact),
        (workbook, CFG.sourceFileLocation, Literal(str(tmp_path / "published-workbook.xlsx"))),
        (workbook, CFG.ruleDataSheetName, Literal("Published governed rules")),
        (experience, RDF.type, CFG.UserExperienceProfile),
        (experience, CFG.showsDeveloperDiagnostics, Literal(True)),
        (operator_profile, RDF.type, extension_class),
    ):
        configuration.add(triple)
    # The vocabulary deliberately defines no cfg individuals or imported RDF/
    # RDFS built-ins. Those are not undefined configuration class/property uses.
    for individual in (application, collection, workbook, experience):
        assert not list(vocabulary.predicate_objects(individual))
    configuration_path = tmp_path / "configuration.ttl"
    vocabulary_path = tmp_path / "configuration-vocabulary.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    vocabulary.serialize(destination=vocabulary_path, format="turtle")
    saved_files = {path: path.read_bytes() for path in (configuration_path, vocabulary_path)}
    configuration_graph = Graph().parse(configuration_path, format="turtle")
    vocabulary_graph = Graph().parse(vocabulary_path, format="turtle")
    original_configuration = _copy(configuration_graph)
    original_vocabulary = _copy(vocabulary_graph)

    result = _validator()(
        configuration_graph=configuration_graph,
        vocabulary_graph=vocabulary_graph,
    )

    assert getattr(result, "conforms", None) is True, (
        "IT-62R1S1 requires configuration RDF to pass when every used configuration "
        "class and property has an explicit vocabulary definition."
    )
    assert result.undefined_classes == ()
    assert result.undefined_properties == ()
    assert isomorphic(configuration_graph, original_configuration), "Validation changed configuration knowledge."
    assert isomorphic(vocabulary_graph, original_vocabulary), "Validation changed vocabulary definitions."
    assert {path: path.read_bytes() for path in saved_files} == saved_files
