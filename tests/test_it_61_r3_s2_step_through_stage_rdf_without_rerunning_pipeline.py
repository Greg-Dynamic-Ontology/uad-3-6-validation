"""IT-61R3S2: next/previous display the selected saved stage without construction.

Follow existing rendered previous/next links on the run page in paused mode.
The exact original Turtle, complete RDF graph, selected result IRI and visible
stage heading must change together. All construction entry points and workbook
reading are blocked during navigation; no source workbook is supplied.
Blank-node equivalence is checked by RDF isomorphism. Helpers are self-contained.
"""
from hashlib import sha256
from importlib import import_module
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import PROV, XSD
from rdflib.util import from_n3

from app.main import app
from app.services.construction_exchange import UADEX, record_construction_stage_result

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
STAGES = ("normalized-constraint-representation", "logical-schema-binding", "context-resolution")


class _RdfPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.run_ids = []
        self.selected = []
        self.links = []
        self.edge_terms = []
        self.node_terms = []
        self.rdf_blocks = []
        self._rdf_parts = None
        self._svg_depth = 0
        self.incomplete_rdf_edges = 0
        self.unescaped_source_markup = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-selected-stage-result-id" in attrs:
            self.selected.append(attrs["data-selected-stage-result-id"])
        if tag == "a" and attrs.get("data-visualization-action") == "select":
            self.links.append(attrs.get("href", ""))
        if tag == "svg":
            self._svg_depth += 1
        if self._svg_depth and "data-rdf-subject" in attrs:
            keys = ("data-rdf-subject-n3", "data-rdf-predicate-n3", "data-rdf-object-n3")
            if not all(key in attrs for key in keys):
                self.incomplete_rdf_edges += 1
            else:
                self.edge_terms.append(tuple(attrs[key] for key in keys))
        if self._svg_depth and "data-rdf-term-n3" in attrs:
            self.node_terms.append(attrs["data-rdf-term-n3"])
        if tag == "pre" and attrs.get("id") == "stage-rdf":
            self._rdf_parts = []
        if tag == "governed-note":
            self.unescaped_source_markup = True

    def handle_data(self, data):
        if self._rdf_parts is not None:
            self._rdf_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "svg":
            self._svg_depth -= 1
        if tag == "pre" and self._rdf_parts is not None:
            self.rdf_blocks.append(''.join(self._rdf_parts))
            self._rdf_parts = None


def _files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


class _SteppingPage(_RdfPage):
    def __init__(self):
        super().__init__()
        self.controls = {}
        self.headings = []
        self._heading_parts = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        attributes = dict(attrs)
        action = attributes.get("data-visualization-action")
        if tag == "a" and action in ("previous", "next") and attributes.get("aria-disabled") != "true":
            self.controls.setdefault(action, []).append(attributes.get("href", ""))
        if tag == "h2":
            self._heading_parts = []

    def handle_data(self, data):
        super().handle_data(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if tag == "h2" and self._heading_parts is not None:
            self.headings.append(" ".join("".join(self._heading_parts).split()))
            self._heading_parts = None


@pytest.mark.parametrize("first_action, neighbor_index", [("next", 2), ("previous", 0)],
                         ids=["next-then-previous", "previous-then-next"])
def test_it_61_r3_s2_steps_between_saved_stage_rdf_without_rerunning_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    first_action: str, neighbor_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it61r3s2:{uuid4().hex}:")
    token = uuid4().hex
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    output_root = tmp_path / "build-runs"
    directory = output_root / token
    row_directory = directory / "constraints" / uuid4().hex
    row_directory.mkdir(parents=True)
    configuration = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.usesConstraintBuildProfile, ns.profile),
        (ns.profile, RDF.type, CFG.ConstraintBuildProfile),
        (ns.profile, CFG.buildOutputDirectory, Literal(str(output_root))),
    ):
        configuration.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)
    knowledge = Graph()
    knowledge.bind("test", ns)
    knowledge.bind("cv", CV)
    knowledge.add((ns.constraint, RDF.type, CV.NormalizedConstraint))
    knowledge.add((ns.constraint, CV.governedUniqueId, Literal("0" + uuid4().hex)))
    knowledge.add((ns.constraint, PROV.wasDerivedFrom, ns.source_row))
    knowledge.add((ns.constraint, CV.requirementText,
                   Literal('Governed text & <governed-note>quoted "value"</governed-note> — café')))
    # Equal lexical spellings with distinct RDF identities must not collapse.
    for value in (Literal("present", lang="en"), Literal("present", lang="fr")):
        knowledge.add((ns.constraint, ns.annotation, value))
    knowledge.add((ns.constraint, ns.threshold, Literal("7", datatype=XSD.integer)))
    knowledge.add((ns.constraint, ns.threshold, Literal("7", datatype=XSD.string)))
    knowledge.add((ns.constraint, ns.reference, ns.named_resource))
    knowledge.add((ns.constraint, ns.reference, Literal(str(ns.named_resource))))
    head = BNode()
    knowledge.add((ns.constraint, ns.ordered_schema_path, head))
    Collection(knowledge, head, [ns.property_resource, ns.address_resource])
    batch = Graph()
    snapshots = []
    for index, stage in enumerate(STAGES):
        if index:
            knowledge.add((ns.constraint, CV.logicalSchemaResource, ns.address_resource))
        if index == 2:
            knowledge.add((ns.constraint, CV.applicableContext, ns.resolved_context))
        record = record_construction_stage_result(
            output_graph=knowledge, constraint_id=str(ns.constraint),
            construction_stage=stage, construction_status="GREEN",
        )
        knowledge.add((record.result_id, UADEX.availableForDownstream, Literal(True)))
        path = row_directory / f"{index + 1:02d}-{stage}.ttl"
        knowledge.add((record.result_id, UADEX.rdfSnapshotPath, Literal(str(path))))
        turtle = f"# Original governed serialization {uuid4().hex}\n\n" + knowledge.serialize(format="turtle")
        path.write_bytes(turtle.encode("utf-8"))
        for triple in knowledge:
            batch.add(triple)
        batch.set((record.result_id, UADEX.snapshotSha256, Literal(sha256(path.read_bytes()).hexdigest())))
        snapshots.append((record.result_id, path, turtle))
    batch_path = directory / "batch-results.ttl"
    batch.serialize(destination=batch_path, format="turtle")
    manifest = Graph()
    for triple in (
        (run, RDF.type, CV.ConstraintPipelineRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.sourceWorkbook, ns.workbook),
        (run, CV.sourceWorksheet, Literal("GovernedRules")),
        (run, CV.status, Literal("COMPLETE")),
        (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
    ):
        manifest.add(triple)
    manifest.serialize(destination=directory / "run.ttl", format="turtle")
    originals = _files(tmp_path)
    attempted = []
    routes = import_module("app.api.routes")
    pipeline = import_module("app.services.constraint_production_pipeline")
    workbench = import_module("app.services.constraint_pipeline_workbench")

    def forbid(name):
        def rejected(*args, **kwargs):
            attempted.append(name)
            pytest.fail(f"IT-61R3S2 stage navigation must not rerun construction: {name}")
        return rejected

    operations = (
        ("constraint_production_pipeline", "process_governed_source_row"),
        ("constraint_production_pipeline", "process_all_governed_source_rows"),
        ("constraint_production_pipeline", "resume_governed_source_row"),
        ("constraint_production_pipeline", "_construct_governed_source"),
        ("constraint_pipeline_workbench", "process_one_workbook_row"),
        ("constraint_pipeline_workbench", "process_selected_workbook_rows"),
        ("constraint_pipeline_workbench", "process_all_workbook_rows"),
        ("constraint_pipeline_workbench", "list_workbook_row_identifiers"),
        ("constraint_set_build_workbench", "build_registered_constraint_set"),
        ("constraint_normalization_agent", "normalize_governed_constraint_to_file"),
        ("logical_schema_binding_agent", "bind_normalized_constraint_to_logical_schema"),
        ("context_resolution_agent", "resolve_bound_constraint_context"),
        ("constraint_behavior_classification", "classify_governed_constraint_behavior"),
        ("instance_rdf_binding_agent", "bind_governed_constraint_to_instance_rdf"),
        ("shacl_generation_agent", "generate_governed_constraint_shacl"),
    )
    for module_name, operation_name in operations:
        module = import_module(f"app.services.{module_name}")
        real = getattr(module, operation_name)
        blocked = forbid(f"{module_name}.{operation_name}")
        monkeypatch.setattr(module, operation_name, blocked)
        for consumer in (routes, pipeline, workbench):
            if getattr(consumer, operation_name, None) is real:
                monkeypatch.setattr(consumer, operation_name, blocked)
    for module in (pipeline, workbench):
        monkeypatch.setattr(module, "load_workbook", forbid("load_workbook"))
    url = f"/constraint-workbench/runs/{token}"

    def assert_display(response, index):
        assert response.status_code == 200
        page = _SteppingPage()
        page.feed(response.text)
        result, path, turtle = snapshots[index]
        assert page.run_ids == [str(run)]
        assert page.selected == [str(result)], "Navigation displayed another stage's result identity."
        assert page.rdf_blocks == [turtle], "Navigation did not display the selected stage's exact Turtle."
        assert any(STAGES[index] in heading for heading in page.headings), (
            "Identify the actual stage associated with the displayed RDF."
        )
        rendered = Graph()
        assert page.edge_terms and not page.incomplete_rdf_edges
        for edge in page.edge_terms:
            rendered.add(tuple(from_n3(term) for term in edge))
        assert isomorphic(rendered, Graph().parse(path, format="turtle"))
        assert len(page.edge_terms) == len(rendered)
        assert not page.unescaped_source_markup
        assert _files(tmp_path) == originals
        return page

    def navigation_link(page, action, index):
        links = page.controls.get(action, [])
        assert len(links) == 1, f"Provide one active {action} stage control."
        target = urlsplit(links[0])
        assert not target.scheme and not target.netloc and target.path == url
        query = parse_qs(target.query)
        assert query.get("result_id") == [str(snapshots[index][0])]
        assert query.get("playback") == ["paused"]
        return links[0]

    with TestClient(app, follow_redirects=False) as client:
        middle = assert_display(client.get(url, params={
            "result_id": str(snapshots[1][0]), "playback": "paused",
        }), 1)
        neighbor = assert_display(client.get(navigation_link(middle, first_action, neighbor_index)), neighbor_index)
        reverse = "previous" if first_action == "next" else "next"
        assert_display(client.get(navigation_link(neighbor, reverse, 1)), 1)
    assert not attempted
    assert _files(tmp_path) == originals
