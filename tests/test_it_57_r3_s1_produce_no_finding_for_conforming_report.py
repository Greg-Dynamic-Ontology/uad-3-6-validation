"""IT-57R3S1: produce no finding for a real conforming SHACL report."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.collection import Collection
from rdflib.namespace import PROV, SH

from app.services.shacl_generation_agent import generate_governed_constraint_shacl
from app.services.validation_finding_projection import project_governed_findings


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def test_it_57_r3_s1_produces_no_finding_for_conforming_validation_report(
    tmp_path: Path,
) -> None:
    ns = Namespace(f"urn:uad36:test:it57r3s1:{uuid4().hex}:")
    constraint = ns.constraint
    source = ns.source_constraint
    source_rule = ns.source_rule
    focus = ns.appraisal_property
    violation_kind = ns.MissingRequiredValue
    severity = "Fatal"
    requirement = Literal("Provide the governed value for each applicable property.")
    bound = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, Literal("The governed value is absent.")),
        (constraint, CV.sourceConstraint, source),
        (constraint, CV.umdpRule, source_rule),
        (constraint, CV.severity, Literal(severity)),
        (constraint, CV.violationKind, violation_kind),
        (constraint, PROV.wasDerivedFrom, source),
        (constraint, CV.boundLogicalSchemaResource, ns.value_qname),
        (constraint, CV.applicableContext, ns.context),
        (constraint, CV.behaviorClassification, ns.classification),
        (constraint, CV.instanceRdfBinding, ns.binding),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
        (ns.classification, RDF.type, CV.ValidationBehaviorClassification),
        (ns.classification, CV.applicableContext, ns.context),
        (ns.classification, CV.validationBehavior, ns.behavior),
        (ns.behavior, RDF.type, CV.ValidationBehavior),
        (ns.binding, RDF.type, CV.InstanceRdfBinding),
        (ns.binding, CV.boundLogicalSchemaResource, ns.value_qname),
        (ns.binding, CV.applicableContext, ns.context),
        (ns.binding, CV.behaviorClassification, ns.classification),
        (ns.binding, CV.validationBehavior, ns.behavior),
        (ns.binding, CV.focusClass, ns.Property),
        (ns.binding, CV.valuePredicate, ns.required_value),
        (ns.binding, CV.predicatePath, ns.predicate_path),
    ):
        bound.add(triple)
    Collection(bound, ns.schema_path, [ns.property_qname, ns.value_qname])
    Collection(bound, ns.predicate_path, [ns.required_value])
    patterns = Graph()
    patterns.add((ns.behavior, CV.shaclImplementationPattern, ns.pattern))
    patterns.add((ns.pattern, RDF.type, CV.ShaclImplementationPattern))
    patterns.add((ns.pattern, CV.propertyShapeTemplate, ns.template))
    patterns.add((ns.template, RDF.type, SH.PropertyShape))
    patterns.add((ns.template, SH.minCount, Literal(1)))

    # Production generation supplies the executable shape and constraint
    # linkage. The test does not add a synthetic source-shape shortcut.
    governed = Graph()
    artifact = tmp_path / "governed-shapes" / "constraint.ttl"
    generate_governed_constraint_shacl(
        bound_graph=bound,
        implementation_patterns_graph=patterns,
        constraint_id=str(constraint),
        output_path=artifact,
        output_graph=governed,
    )
    assert artifact.is_file()
    shapes = Graph().parse(artifact, format="turtle")
    representations = set(governed.objects(constraint, CV.shaclRepresentation))
    assert len(representations) == 1
    shape = next(iter(representations))
    assert (shape, CV.implementsConstraint, constraint) in governed
    property_shapes = set(shapes.objects(shape, SH.property))
    assert len(property_shapes) == 1
    property_shape = next(iter(property_shapes))

    # The rule is genuinely applicable and all finding metadata is present.
    # Supply its value so the real validator produces no violation.
    instance = Graph()
    instance.add((focus, RDF.type, ns.Property))
    instance.add((focus, ns.required_value, Literal("Supplied governed value")))
    assert (constraint, CV.sourceConstraint, source) in governed
    assert (constraint, CV.umdpRule, source_rule) in governed
    assert (constraint, CV.severity, Literal(severity)) in governed
    assert (constraint, CV.violationKind, violation_kind) in governed
    conforms, runtime_report, _ = validate(data_graph=instance, shacl_graph=shapes)
    assert conforms, "The supplied-value fixture must conform to the generated shape."
    report = Graph().parse(
        data=runtime_report.serialize(format="turtle"), format="turtle"
    )
    reports = set(report.subjects(RDF.type, SH.ValidationReport))
    assert len(reports) == 1
    report_node = next(iter(reports))
    assert (report_node, SH.conforms, Literal(True)) in report
    assert not list(report.subjects(RDF.type, SH.ValidationResult))
    assert not list(report.objects(report_node, SH.result))
    report_before = set(report)
    governed_before = set(governed)

    projected = project_governed_findings(
        shacl_result_graph=report,
        governed_constraint_graph=governed,
    )
    assert projected.findings == [], (
        "IT-57R3S1 requires no governed finding when an applicable constraint "
        "has no SHACL violation. Do not convert successful validation into "
        "an informational, placeholder, or failure finding."
    )
    assert set(report) == report_before
    assert set(governed) == governed_before
    repeated = project_governed_findings(
        shacl_result_graph=report,
        governed_constraint_graph=governed,
    )
    assert repeated.findings == []
    assert set(report) == report_before
    assert set(governed) == governed_before