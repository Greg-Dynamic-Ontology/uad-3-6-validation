"""Transactional customer RDF persistence backed by GraphDB."""

import json
from hashlib import sha256
from collections.abc import Mapping
from datetime import datetime, timezone
from io import BytesIO
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD
from rdflib.compare import to_canonical_graph


PROV = Namespace("http://www.w3.org/ns/prov#")
PROVENANCE_GRAPH = "urn:uad:customer:provenance"
CHANGE = Namespace("urn:uad:customer:change:")
SHAPE_META = Namespace("urn:owb:graphdb:shape-set:")
SHAPE_METADATA_GRAPH = "urn:owb:graphdb:shape-set-metadata"
INSTALLED_SHAPE_SET = URIRef("urn:owb:graphdb:installed-shape-set")
REQUEST_TIMEOUT_SECONDS = 30


def _iri(value: str) -> URIRef:
    """Require an absolute IRI safe for use in a SPARQL graph reference."""
    forbidden = '<>"{}|\\^`'
    if (
        not value
        or not urlsplit(value).scheme
        or any(ord(character) <= 32 or character in forbidden for character in value)
    ):
        raise ValueError(f"Expected an absolute RDF IRI: {value!r}")
    return URIRef(value)


class CommitOutcomeUnconfirmedError(RuntimeError):
    """COMMIT was attempted but its result was not received reliably."""

    code = "commit_outcome_unconfirmed"
    committed = None
    rollback_confirmed = False
    reconciliation_required = True

    def __init__(self, repository_url: str, transaction_url: str, change_iri: str):
        self.repository_url = repository_url
        self.transaction_url = transaction_url
        self.change_iri = change_iri
        super().__init__(
            "Customer transaction commit outcome is unconfirmed. "
            "Reconcile the durable change record before considering a retry."
        )

class PersistenceUnavailableError(RuntimeError):
    """A connection refusal prevented a pre-commit persistence operation."""

    code = "persistence_unavailable"
    committed = False

    def __init__(self, repository_url: str):
        self.repository_url = repository_url
        super().__init__(
            "Customer persistence is unavailable: the GraphDB connection was refused. "
            "The requested change was not committed."
        )

class StaleResourceVersionError(RuntimeError):
    """The caller must refresh a resource before retrying its change."""

    code = "stale_resource_version"
    refresh_required = True

    def __init__(self, resource_iri: str, expected_version: str, actual_version: str):
        self.resource_iri = resource_iri
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Resource '{resource_iri}' has changed. Refresh the resource "
            "and reconsider the update before retrying."
        )

class CustomerValidationError(HTTPError):
    """A rejected transaction with parsed SHACL diagnostics.

    Remains an HTTPError so existing callers can inspect status and read the
    original response body. The transaction URL correlates the attempted change.
    """

    def __init__(self, error, body, report, transaction_url):
        super().__init__(error.url, error.code, error.msg, error.headers, BytesIO(body))
        self.validation_report = report
        self.transaction_url = transaction_url


def _validation_report(body: bytes) -> Graph | None:
    """Extract a nonconforming Turtle report, including JSON-wrapped reports."""
    text = body.decode("utf-8", errors="replace")
    candidates = [text]

    def collect_strings(value):
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                collect_strings(item)
        elif isinstance(value, list):
            for item in value:
                collect_strings(item)

    try:
        collect_strings(json.loads(text))
    except (ValueError, RecursionError):
        pass

    sh = Namespace("http://www.w3.org/ns/shacl#")
    for candidate in candidates:
        variants = [candidate]
        for marker in ("@prefix", "PREFIX "):
            position = candidate.find(marker)
            if position > 0:
                variants.append(candidate[position:])
        for variant in variants:
            report = Graph()
            try:
                report.parse(data=variant, format="turtle")
            except Exception:
                continue
            for node in report.subjects(RDF.type, sh.ValidationReport):
                if (node, sh.conforms, Literal(False)) not in report:
                    continue
                for result in report.objects(node, sh.result):
                    if (
                        any(report.objects(result, sh.focusNode))
                        and any(report.objects(result, sh.sourceConstraintComponent))
                    ):
                        return report
    return None


def _with_validation_details(error: HTTPError, transaction_url: str) -> HTTPError:
    """Buffer diagnostics so parsing does not consume the caller's response."""
    try:
        body = error.read()
    except Exception:
        error.add_note("The HTTP error response body could not be read.")
        return error
    error.close()
    report = _validation_report(body)
    if report is None:
        # Ordinary HTTP failures must not be classified as SHACL rejections.
        enriched = HTTPError(error.url, error.code, error.msg, error.headers, BytesIO(body))
    else:
        enriched = CustomerValidationError(error, body, report, transaction_url)
    for note in getattr(error, "__notes__", ()):
        enriched.add_note(note)
    return enriched

class CustomerRdfStore:
    """Commit and retrieve a complete customer graph through GraphDB."""

    def __init__(self, repository_url: str, graph_iri: str) -> None:
        repository_url = repository_url.rstrip("/")
        parsed = urlsplit(repository_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Expected an HTTP(S) GraphDB repository URL.")

        self.repository_url = repository_url
        self.graph_iri = str(_iri(graph_iri))
        if self.graph_iri == PROVENANCE_GRAPH:
            raise ValueError("The customer graph must differ from the provenance graph.")

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        accept: str | None = None,
    ) -> tuple[int, object, bytes]:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if accept:
            headers["Accept"] = accept

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.status, response.headers, response.read()
        except HTTPError:
            # Preserve HTTP responses, especially SHACL rejection reports.
            raise
        except (URLError, ConnectionRefusedError) as error:
            reason = error.reason if isinstance(error, URLError) else error
            action = parse_qs(urlsplit(url).query).get("action", [None])[0]
            # Do not classify a lost COMMIT response, timeout, or connection
            # reset as a confirmed non-commit. Those need outcome reconciliation.
            if isinstance(reason, ConnectionRefusedError) and action != "COMMIT":
                raise PersistenceUnavailableError(self.repository_url) from error
            raise

    @staticmethod
    def _action_url(transaction_url: str, action: str, **parameters: str) -> str:
        return transaction_url + "?" + urlencode({"action": action, **parameters})

    def _read_named_graph(self, graph_iri: str) -> Graph:
        query = urlencode({"context": _iri(graph_iri).n3(), "infer": "false"})
        _, _, body = self._request(
            "GET", self.repository_url + "/statements?" + query,
            accept="application/n-triples",
        )
        return Graph().parse(data=body.decode("utf-8"), format="nt")

    def _installed_shape_version(self) -> str:
        metadata = self._read_named_graph(SHAPE_METADATA_GRAPH)
        versions = list(metadata.objects(INSTALLED_SHAPE_SET, SHAPE_META.version))
        if len(versions) != 1 or not isinstance(versions[0], Literal) or not str(versions[0]).strip():
            raise RuntimeError(
                "Customer attribution requires exactly one installed SHACL shape version."
            )
        return str(versions[0])

    def activate_shape_version(self, *, shapes_path: str | Path, version: str) -> None:
        """Activate caller-approved shapes and metadata in one transaction.

        GraphDB validates the existing data against the changed shapes on
        commit. Keep the existing data-graph mappings and customer RDF intact.
        Approval of the candidate is a caller responsibility.
        """
        if not isinstance(version, str) or not version.strip():
            raise ValueError("Supply a nonempty approved shape version.")
        supplied_bytes = Path(shapes_path).read_bytes()
        candidate = Graph().parse(data=supplied_bytes, format="turtle")
        if not candidate:
            raise ValueError("The approved shape set must not be empty.")
        shape_graph = URIRef("urn:owb:graphdb:shapes")
        metadata = self._read_named_graph(SHAPE_METADATA_GRAPH)
        if set(metadata.objects(INSTALLED_SHAPE_SET, SHAPE_META.shapesGraph)) != {shape_graph}:
            raise RuntimeError("Expected the managed installed customer shape graph.")
        old_versions = list(metadata.objects(INSTALLED_SHAPE_SET, SHAPE_META.version))
        if len(old_versions) != 1:
            raise RuntimeError("Expected exactly one currently installed shape version.")
        mappings = self._read_named_graph("http://rdf4j.org/schema/rdf4j#SHACLShapeGraph")
        sh = Namespace("http://www.w3.org/ns/shacl#")
        if (URIRef(self.graph_iri), sh.shapesGraph, shape_graph) not in mappings:
            raise RuntimeError("The customer graph is not mapped to the managed shapes.")
        digest = sha256(supplied_bytes).hexdigest()
        old_digests = list(metadata.objects(INSTALLED_SHAPE_SET, SHAPE_META.contentDigest))
        if str(old_versions[0]) == version and (
            len(old_digests) != 1 or str(old_digests[0]) != digest
        ):
            raise ValueError("Changed shapes require a different version identifier.")
        metadata.set((INSTALLED_SHAPE_SET, SHAPE_META.version, Literal(version, datatype=XSD.string)))
        metadata.set((INSTALLED_SHAPE_SET, SHAPE_META.contentDigest, Literal(digest, datatype=XSD.string)))
        replacements = (
            (shape_graph, candidate.serialize(format="nt", encoding="utf-8")),
            (URIRef(SHAPE_METADATA_GRAPH), metadata.serialize(format="nt", encoding="utf-8")),
        )

        transactions_url = self.repository_url + "/transactions"
        status, headers, _ = self._request(
            "POST",
            transactions_url,
            body=b"",
            content_type="application/x-www-form-urlencoded",
        )
        if status != 201:
            raise RuntimeError(f"GraphDB transaction creation returned HTTP {status}.")

        location = headers.get("Location")
        if not location:
            raise RuntimeError("GraphDB did not return a transaction Location.")

        transaction_url = urljoin(transactions_url, location)
        repository = urlsplit(self.repository_url)
        transaction = urlsplit(transaction_url)
        if (
            (transaction.scheme, transaction.netloc)
            != (repository.scheme, repository.netloc)
            or not transaction.path.startswith(repository.path + "/transactions/")
            or transaction.query
            or transaction.fragment
        ):
            raise RuntimeError("GraphDB returned an unexpected transaction Location.")

        try:
            # Both replacements remain uncommitted until GraphDB accepts the
            # proposed shapes. A failed activation rolls back both graphs.
            for graph_iri, serialized in replacements:
                self._request(
                    "PUT",
                    self._action_url(transaction_url, "UPDATE", queryLn="SPARQL"),
                    body=f"CLEAR SILENT GRAPH {graph_iri.n3()}".encode("utf-8"),
                    content_type="application/sparql-update; charset=utf-8",
                )
                self._request(
                    "PUT",
                    self._action_url(transaction_url, "ADD", context=graph_iri.n3()),
                    body=serialized,
                    content_type="application/n-triples",
                )
            status, _, _ = self._request(
                "PUT", self._action_url(transaction_url, "COMMIT"), body=b"",
            )
            if status not in {200, 204}:
                raise RuntimeError(f"GraphDB did not confirm shape activation: HTTP {status}.")
        except Exception as error:
            try:
                self._request("DELETE", transaction_url)
            except Exception:
                error.add_note(
                    "GraphDB rollback could not be confirmed. "
                    "Inspect repository state before retrying."
                )
            if isinstance(error, HTTPError):
                enriched = _with_validation_details(error, transaction_url)
                if enriched is not error:
                    raise enriched from error
            raise

    def _resource_version(self, dataset: Graph, resource_iri: str) -> str:
        """Fingerprint explicit outgoing RDF and reachable blank-node details.

        Tokens represent content, not a monotonic revision counter. Equivalent
        RDF string representations and blank-node labels produce the same token.
        """
        resource = _iri(resource_iri)
        selected = Graph()
        pending = [resource]
        visited = set()
        while pending:
            subject = pending.pop()
            if subject in visited:
                continue
            visited.add(subject)
            for _, predicate, obj in dataset.triples((subject, None, None)):
                if isinstance(obj, BNode):
                    pending.append(obj)
                elif isinstance(obj, Literal) and obj.datatype is None and obj.language is None:
                    obj = Literal(str(obj), datatype=XSD.string)
                selected.add((subject, predicate, obj))
        lines = sorted(
            " ".join(term.n3() for term in triple) + " ."
            for triple in to_canonical_graph(selected)
        )
        payload = "\n".join([self.graph_iri, str(resource), *lines])
        return "sha256:" + sha256(payload.encode("utf-8")).hexdigest()

    def get_resource_version(self, resource_iri: str) -> str:
        """Return an opaque content token derived from persisted customer RDF."""
        resource = str(_iri(resource_iri))
        return self._resource_version(self.retrieve(), resource)

    def _check_resource_versions(self, expected_versions: Mapping[str, str]) -> None:
        # One persisted graph read gives a common view for all expected tokens.
        # This detects an update already committed before this check. It is not
        # a database compare-and-swap lock against a later simultaneous writer.
        persisted = self.retrieve()
        for resource, expected in expected_versions.items():
            actual = self._resource_version(persisted, resource)
            if actual != expected:
                raise StaleResourceVersionError(resource, expected, actual)

    def commit(self, dataset: Graph, *, actor_id: str) -> None:
        """Replace the complete customer graph in one validated transaction."""
        self._commit_graph(dataset, actor_id=actor_id, replace=True, removals=None)

    def apply_change(
        self, *, additions: Graph, removals: Graph, actor_id: str,
        expected_versions: Mapping[str, str] | None = None,
    ) -> None:
        """Apply exact triple removals followed by additions atomically.

        Preserve all other customer triples. GraphDB validates the resulting
        dataset at commit; rejection is raised to the caller without retries.
        Removals must use stable RDF terms, not response-local blank-node IDs.
        """
        if not isinstance(additions, Graph) or not isinstance(removals, Graph):
            raise TypeError("additions and removals must be RDF graphs.")
        if any(isinstance(term, BNode) for triple in removals for term in triple):
            raise ValueError("Incremental removals require triples without blank nodes.")
        self._commit_graph(
            additions, actor_id=actor_id, replace=False, removals=removals,
            expected_versions=expected_versions,
        )

    def _commit_graph(
        self, dataset: Graph, *, actor_id: str, replace: bool,
        removals: Graph | None,
        expected_versions: Mapping[str, str] | None = None,
    ) -> None:
        actor = _iri(actor_id)
        if expected_versions is not None:
            if not isinstance(expected_versions, Mapping):
                raise TypeError("expected_versions must map resource IRIs to version tokens.")
            expected_versions = dict(expected_versions)
            for resource, version in expected_versions.items():
                _iri(resource)
                if not isinstance(version, str) or not version:
                    raise ValueError("Expected resource versions must be nonempty strings.")
        customer_graph = URIRef(self.graph_iri)
        customer_data = dataset.serialize(format="nt", encoding="utf-8")

        # Read the installed metadata rather than accepting a caller's claimed
        # validation version. Missing attribution metadata fails before writing.
        shape_version = self._installed_shape_version()
        affected_resources = set(dataset.subjects())
        if replace:
            # Include resources removed by a whole-graph replacement as well.
            affected_resources.update(self.retrieve().subjects())
        elif removals is not None:
            affected_resources.update(removals.subjects())

        activity = URIRef(f"urn:uad:customer-change:{uuid4()}")
        provenance = Graph()
        provenance.add((activity, RDF.type, PROV.Activity))
        provenance.add((activity, PROV.wasAssociatedWith, actor))
        provenance.add((activity, PROV.generated, customer_graph))
        for resource in affected_resources:
            provenance.add((activity, CHANGE.affectedResource, resource))
        provenance.add((activity, CHANGE.operation, Literal("replace" if replace else "patch")))
        provenance.add((activity, CHANGE.shapeVersion, Literal(shape_version)))
        provenance.add((
            activity,
            PROV.startedAtTime,
            Literal(datetime.now(timezone.utc), datatype=XSD.dateTime),
        ))
        provenance_data = provenance.serialize(format="nt", encoding="utf-8")

        transactions_url = self.repository_url + "/transactions"
        status, headers, _ = self._request(
            "POST",
            transactions_url,
            body=b"",
            content_type="application/x-www-form-urlencoded",
        )
        if status != 201:
            raise RuntimeError(f"GraphDB transaction creation returned HTTP {status}.")

        location = headers.get("Location")
        if not location:
            raise RuntimeError("GraphDB did not return a transaction Location.")

        transaction_url = urljoin(transactions_url, location)
        repository = urlsplit(self.repository_url)
        transaction = urlsplit(transaction_url)
        if (
            (transaction.scheme, transaction.netloc)
            != (repository.scheme, repository.netloc)
            or not transaction.path.startswith(repository.path + "/transactions/")
            or transaction.query
            or transaction.fragment
        ):
            raise RuntimeError("GraphDB returned an unexpected transaction Location.")

        commit_requested = False
        try:
            if expected_versions:
                self._check_resource_versions(expected_versions)
            if replace:
                self._request(
                    "PUT",
                    self._action_url(transaction_url, "UPDATE", queryLn="SPARQL"),
                    body=f"CLEAR SILENT GRAPH {customer_graph.n3()}".encode("utf-8"),
                    content_type="application/sparql-update; charset=utf-8",
                )
            elif removals is not None and len(removals):
                # Ground RDF terms are serialized by RDFLib, not interpolated
                # from unescaped user strings. No read/replace cycle is used.
                triples = removals.serialize(format="nt", encoding="utf-8").decode("utf-8")
                update = f"DELETE DATA {{ GRAPH {customer_graph.n3()} {{\n{triples}\n}} }}"
                self._request(
                    "PUT",
                    self._action_url(transaction_url, "UPDATE", queryLn="SPARQL"),
                    body=update.encode("utf-8"),
                    content_type="application/sparql-update; charset=utf-8",
                )
            self._request(
                "PUT",
                self._action_url(
                    transaction_url,
                    "ADD",
                    context=customer_graph.n3(),
                ),
                body=customer_data,
                content_type="application/n-triples",
            )
            self._request(
                "PUT",
                self._action_url(
                    transaction_url,
                    "ADD",
                    context=URIRef(PROVENANCE_GRAPH).n3(),
                ),
                body=provenance_data,
                content_type="application/n-triples",
            )
            commit_requested = True
            status, _, _ = self._request(
                "PUT",
                self._action_url(transaction_url, "COMMIT"),
                body=b"",
            )
            if status not in {200, 204}:
                raise RuntimeError(
                    f"GraphDB did not confirm the transaction commit: HTTP {status}."
                )
        except Exception as error:
            # Once COMMIT has been sent, a transport failure cannot prove
            # rollback. The server may have durably committed both graphs.
            transport_failure = (
                isinstance(error, (URLError, OSError, HTTPException))
                and not isinstance(error, HTTPError)
            )
            if commit_requested and transport_failure:
                raise CommitOutcomeUnconfirmedError(
                    self.repository_url, transaction_url, str(activity),
                ) from error
            try:
                self._request("DELETE", transaction_url)
            except Exception:
                error.add_note(
                    "GraphDB rollback could not be confirmed. "
                    "Inspect repository state before retrying."
                )
            if isinstance(error, HTTPError):
                enriched = _with_validation_details(error, transaction_url)
                if enriched is not error:
                    raise enriched from error
            raise

    def reconcile_change(self, *, change_iri: str) -> dict:
        """Read durable attribution without retrying or rolling back a change.

        A complete activity for this graph proves that the transaction containing
        it committed. Absence is not proof of rollback: the transaction may still
        be in flight. Neither outcome here authorizes automatic replay.
        """
        change = _iri(change_iri)
        result = {
            "change_iri": str(change),
            "outcome": "unconfirmed",
            "retry_allowed": False,
        }
        try:
            records = self._read_named_graph(PROVENANCE_GRAPH)
        except (URLError, OSError, HTTPException, PersistenceUnavailableError):
            result["diagnostic"] = "Durable attribution could not be read; outcome remains unconfirmed."
            return result
        complete = (
            (change, RDF.type, PROV.Activity) in records
            and (change, PROV.generated, URIRef(self.graph_iri)) in records
            and len(list(records.objects(change, PROV.wasAssociatedWith))) == 1
            and len(list(records.objects(change, PROV.startedAtTime))) == 1
            and len(list(records.objects(change, CHANGE.operation))) == 1
            and len(list(records.objects(change, CHANGE.shapeVersion))) == 1
        )
        if complete:
            result["outcome"] = "committed"
        else:
            result["diagnostic"] = "No complete matching durable change record was found. Do not retry."
        return result

    def retrieve(self) -> Graph:
        """Read explicit customer triples, preserving RDF terms and datatypes."""
        query = urlencode({
            "context": URIRef(self.graph_iri).n3(),
            "infer": "false",
        })
        _, _, body = self._request(
            "GET",
            self.repository_url + "/statements?" + query,
            accept="application/n-triples",
        )

        result = Graph()
        result.parse(data=body.decode("utf-8"), format="nt")
        return result






