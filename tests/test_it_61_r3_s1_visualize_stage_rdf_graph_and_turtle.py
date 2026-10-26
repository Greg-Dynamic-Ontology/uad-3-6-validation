"""IT-61R3S1: the displayed graph and exact Turtle preserve RDF term meaning.

The existing SVG lexical edge attributes cannot distinguish an IRI from an
identical-looking literal, or literals with different language/datatype tags.
Proposed additional SVG metadata: each edge exposes data-rdf-subject-n3,
data-rdf-predicate-n3, data-rdf-object-n3; subject/object nodes expose
 data-rdf-term-n3. These full RDF terms allow verification of the rendered graph.
Legacy attributes remain available for existing UI contracts.

Graph equivalence uses RDF isomorphism, not unstable blank-node labels. Original
Turtle comments/formatting must remain available in pre#stage-rdf. Fixtures and
helpers are self-contained and no construction or appraisal evaluation occurs.
"""

from hashlib import sha256
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
STAGES = ("normalized-constraint-representation", "logical-schema-binding")


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


@pytest.mark.parametrize("stage_index", [0, 1], ids=["normalized-rdf", "logical-schema-bound-rdf"])
def test_it_61_r3_s1_graph_and_turtle_represent_the_same_complete_rdf_knowledge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it61r3s1:{uuid4().hex}:")
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
    result_id, path, turtle = snapshots[stage_index]
    url = f"/constraint-workbench/runs/{token}"
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(url, params={"playback": "paused"})
        assert response.status_code == 200
        page = _RdfPage()
        page.feed(response.text)
        links = [href for href in page.links
                 if urlsplit(href).path == url
                 and parse_qs(urlsplit(href).query).get("result_id") == [str(result_id)]]
        assert len(links) == 1
        response = client.get(links[0])
    assert response.status_code == 200
    page = _RdfPage()
    page.feed(response.text)
    assert page.run_ids == [str(run)] and page.selected == [str(result_id)]
    assert page.rdf_blocks == [turtle], "Provide the exact saved Turtle serialization."
    assert not page.unescaped_source_markup
    assert page.edge_terms and page.incomplete_rdf_edges == 0, (
        "IT-61R3S1 requires graph edges to preserve complete RDF terms, including "
        "blank-node identity, literal datatype and language tags; lexical strings alone are insufficient."
    )
    rendered = Graph()
    for edge in page.edge_terms:
        terms = tuple(from_n3(term) for term in edge)
        assert all(term is not None for term in terms)
        rendered.add(terms)
    serialized = Graph().parse(data=page.rdf_blocks[0], format="turtle")
    assert len(page.edge_terms) == len(serialized)
    assert isomorphic(rendered, serialized), "The displayed graph differs from its Turtle serialization."
    assert isomorphic(rendered, Graph().parse(path, format="turtle"))
    displayed_nodes = {from_n3(term) for term in page.node_terms}
    assert {term for subject, _, obj in rendered for term in (subject, obj)} <= displayed_nodes, (
        "Visual nodes must retain distinct RDF identities, including same-spelling literals and IRIs."
    )
    assert _files(tmp_path) == originals
