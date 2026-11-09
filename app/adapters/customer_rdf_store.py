"""Transactional customer RDF persistence backed by GraphDB."""

import json
from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD


PROV = Namespace("http://www.w3.org/ns/prov#")
PROVENANCE_GRAPH = "urn:uad:customer:provenance"
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

    @staticmethod
    def _request(
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
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.status, response.headers, response.read()

    @staticmethod
    def _action_url(transaction_url: str, action: str, **parameters: str) -> str:
        return transaction_url + "?" + urlencode({"action": action, **parameters})

    def commit(self, dataset: Graph, *, actor_id: str) -> None:
        """Replace the customer graph and record attribution atomically.

        SHACL validation is performed by the configured GraphDB repository.
        Return only after GraphDB confirms the transaction commit.
        """
        actor = _iri(actor_id)
        customer_graph = URIRef(self.graph_iri)
        customer_data = dataset.serialize(format="nt", encoding="utf-8")

        activity = URIRef(f"urn:uad:customer-change:{uuid4()}")
        provenance = Graph()
        provenance.add((activity, RDF.type, PROV.Activity))
        provenance.add((activity, PROV.wasAssociatedWith, actor))
        provenance.add((activity, PROV.generated, customer_graph))
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

        try:
            # Replace only this store's customer graph. This also makes
            # repeated writes containing blank nodes deterministic.
            self._request(
                "PUT",
                self._action_url(transaction_url, "UPDATE", queryLn="SPARQL"),
                body=f"CLEAR SILENT GRAPH {customer_graph.n3()}".encode("utf-8"),
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
