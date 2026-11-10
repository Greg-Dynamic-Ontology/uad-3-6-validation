
"""Transactional customer RDF persistence backed by GraphDB."""

import json
from hashlib import sha256
from collections.abc import Mapping
from datetime import datetime, timezone
from dataclasses import asdict
from io import BytesIO
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD
from rdflib.compare import to_canonical_graph

from app.services.customer_accounts import (
    CustomerAccount, CustomerAccountMembership, CustomerAccountRole,
)


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
    if getattr(error, "rollback_confirmed", False) is True:
        enriched.rollback_confirmed = True
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
                rollback_status, _, _ = self._request("DELETE", transaction_url)
                if rollback_status not in {200, 204}:
                    raise RuntimeError("GraphDB did not confirm transaction rollback.")
                # Report explicit evidence to higher-level account creation.
                # Preserve the original exception for existing RDF-store callers.
                if not commit_requested:
                    error.rollback_confirmed = True
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

class AccountCreationIncompleteError(RuntimeError):
    """Account persistence failed before commit and rollback was confirmed."""

    code = "account_creation_incomplete"
    committed = False
    rollback_confirmed = True

    def __init__(self, customer_account_id: str):
        self.customer_account_id = customer_account_id
        super().__init__(
            "Account creation did not complete. The transaction was rolled back; "
            "neither the customer account nor its owner membership was committed."
        )

class GraphDBCustomerAccountRepository:
    """Create and reload account aggregates in the configured customer graph.

    Authentication and eligibility are service prerequisites. Creation writes
    the account, initial membership, and durable attribution in one transaction.
    Each get reads GraphDB; there is no local aggregate cache or fallback file.
    """

    CUSTOMER = Namespace("urn:uad:customer:")
    ROLE_IRIS = {
        CustomerAccountRole.OWNER: CUSTOMER.Owner,
        CustomerAccountRole.BILLING_ADMINISTRATOR: CUSTOMER.BillingAdministrator,
        CustomerAccountRole.VALIDATOR: CUSTOMER.Validator,
        CustomerAccountRole.REVIEWER: CUSTOMER.Reviewer,
    }
    TEXT_FIELDS = {
        "display_name": CUSTOMER.name,
        "account_type": CUSTOMER.accountType,
        "status": CUSTOMER.status,
        "primary_contact_name": CUSTOMER.primaryContactName,
        "primary_contact_email": CUSTOMER.primaryContactEmail,
        "company_name": CUSTOMER.companyName,
        "contact_telephone": CUSTOMER.contactTelephone,
        "postal_address": CUSTOMER.postalAddress,
        "company_website": CUSTOMER.companyWebsite,
    }

    REQUEST_FIELDS = {
        "creation_request_id": CUSTOMER.creationRequestId,
        "creation_request_actor_id": CUSTOMER.creationRequestActorId,
        "creation_request_fingerprint": CUSTOMER.creationRequestFingerprint,
    }

    def __init__(self, *, repository_url: str, graph_iri: str):
        self.store = CustomerRdfStore(repository_url, graph_iri)

    @staticmethod
    def _user_iri(human_user_id: str) -> URIRef:
        if not isinstance(human_user_id, str) or not human_user_id.strip():
            raise ValueError("An identified UAD user is required.")
        if urlsplit(human_user_id).scheme:
            return _iri(human_user_id)
        return URIRef("urn:uad:user:" + quote(human_user_id, safe=""))

    def add(self, customer_account: CustomerAccount) -> None:
        account = _iri(customer_account.customer_account_id)
        if customer_account.status != "active":
            raise ValueError("A new customer account must be active.")
        if customer_account.account_type not in {"solo", "company"}:
            raise ValueError("A new customer account must be solo or company.")
        memberships = customer_account.memberships
        if len(memberships) != 1:
            raise ValueError("Account creation requires exactly one initial owner membership.")
        owner = memberships[0]
        if (
            not owner.active
            or owner.role != CustomerAccountRole.OWNER
            or owner.customer_account_id != str(account)
        ):
            raise ValueError("Account creation requires an active owner in the same account.")
        user = self._user_iri(owner.human_user_id)
        created_at = customer_account.created_at
        if not isinstance(created_at, datetime) or created_at.utcoffset() is None:
            raise ValueError("Account creation time must have a timezone.")
        # This detects an existing ID, not concurrent request idempotency.
        existing = self.store.retrieve()
        if any(existing.triples((account, None, None))):
            raise ValueError("The customer-account ID already exists.")

        customer = self.CUSTOMER
        additions = Graph()
        additions.add((account, RDF.type, customer.CustomerAccount))
        for field_name, predicate in self.TEXT_FIELDS.items():
            value = getattr(customer_account, field_name)
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be text.")
            additions.add((account, predicate, Literal(value, datatype=XSD.string)))
        request_values = {
            name: getattr(customer_account, name)
            for name in self.REQUEST_FIELDS
        }
        if any(request_values.values()):
            if not all(isinstance(value, str) and value.strip() for value in request_values.values()):
                raise ValueError("Creation request metadata must be complete and nonempty.")
            if customer_account.creation_request_actor_id != owner.human_user_id:
                raise ValueError("The creation request actor must match the initial owner.")
            # The service normally returns this existing account before add().
            # This guard detects an intervening completed request; it does not
            # claim to serialize two simultaneous first-time submissions.
            previous = self.find_by_creation_request(
                actor_id=customer_account.creation_request_actor_id,
                request_id=customer_account.creation_request_id,
            )
            if previous is not None:
                raise ValueError("The creation request is already persisted; reload its account.")
            for name, predicate in self.REQUEST_FIELDS.items():
                additions.add((account, predicate, Literal(request_values[name], datatype=XSD.string)))
        additions.add((account, customer.createdAt, Literal(created_at, datatype=XSD.dateTime)))
        additions.add((account, customer.isOwnershipBoundary, Literal(customer_account.is_ownership_boundary)))
        additions.add((account, customer.isBillingBoundary, Literal(customer_account.is_billing_boundary)))
        additions.add((user, RDF.type, customer.User))
        membership = URIRef(f"urn:uad:customer-membership:{uuid4()}")
        additions.add((membership, RDF.type, customer.Membership))
        additions.add((membership, customer.account, account))
        additions.add((membership, customer.user, user))
        additions.add((membership, customer.humanUserId, Literal(owner.human_user_id, datatype=XSD.string)))
        additions.add((membership, customer.role, self.ROLE_IRIS[owner.role]))
        additions.add((membership, customer.active, Literal(True)))
        try:
            self.store.apply_change(additions=additions, removals=Graph(), actor_id=str(user))
        except Exception as error:
            # Do not turn a lost commit response or failed rollback into a false
            # claim that creation did not commit. Only translate confirmed rollback.
            if getattr(error, "rollback_confirmed", False) is True:
                raise AccountCreationIncompleteError(str(account)) from error
            raise

    @staticmethod
    def _one(graph: Graph, subject, predicate):
        values = list(graph.objects(subject, predicate))
        if len(values) != 1:
            raise RuntimeError(f"Expected one stored value for {predicate} on {subject}.")
        return values[0]

    @classmethod
    def _text(cls, graph: Graph, subject, predicate) -> str:
        value = cls._one(graph, subject, predicate)
        if not isinstance(value, Literal):
            raise RuntimeError(f"Expected stored text for {predicate}.")
        return str(value)

    @classmethod
    def _boolean(cls, graph: Graph, subject, predicate) -> bool:
        value = cls._one(graph, subject, predicate)
        if not isinstance(value, Literal) or value.datatype != XSD.boolean:
            raise RuntimeError(f"Expected stored boolean for {predicate}.")
        result = value.toPython()
        if not isinstance(result, bool):
            raise RuntimeError(f"Invalid stored boolean for {predicate}.")
        return result

    @classmethod
    def _optional_text(cls, graph: Graph, subject, predicate) -> str:
        """Accounts created before request tracking have no request fields."""
        if not list(graph.objects(subject, predicate)):
            return ""
        return cls._text(graph, subject, predicate)

    @staticmethod
    def _account_snapshot_version(account: CustomerAccount) -> str:
        """Opaque diagnostic token for the application account snapshot."""
        def encode(value):
            if isinstance(value, datetime):
                return value.isoformat()
            raise TypeError(f"Unsupported snapshot value: {type(value).__name__}")

        payload = json.dumps(
            asdict(account), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, default=encode,
        ).encode("utf-8")
        return "account-snapshot:" + sha256(payload).hexdigest()

    def save_information(
        self, customer_account: CustomerAccount, *, actor_id: str,
        expected_account: CustomerAccount,
    ) -> None:
        """Persist editable fields and attribution in one GraphDB transaction.

        Read authorization from stored memberships. Restrict the RDF patch to
        editable predicates on this account; never replace the customer graph.
        """
        actor = self._user_iri(actor_id)
        account = _iri(customer_account.customer_account_id)
        graph = self.store.retrieve()
        persisted = self._account_from_graph(graph, str(account))
        if persisted.status != "active" or not any(
            membership.active
            and membership.role == CustomerAccountRole.OWNER
            and membership.human_user_id == actor_id
            and membership.customer_account_id == str(account)
            for membership in persisted.memberships
        ):
            raise PermissionError("An active owner of an active account must update its information.")

        # Compare the caller's original read, not a freshly acquired version.
        # Otherwise a stale form could overwrite changes already committed by
        # another administrator before this request reached the adapter.
        if not isinstance(expected_account, CustomerAccount):
            raise TypeError("Supply the account snapshot originally read.")
        if expected_account.customer_account_id != str(account):
            raise ValueError("The expected snapshot must identify the same account.")
        if expected_account != persisted:
            raise StaleResourceVersionError(
                str(account),
                self._account_snapshot_version(expected_account),
                self._account_snapshot_version(persisted),
            )
        # This entry point changes information only, never identity, lifecycle,
        # memberships, original creation details, or ownership boundaries.
        protected_fields = (
            "customer_account_id", "account_type", "status", "memberships",
            "created_at", "is_ownership_boundary", "is_billing_boundary",
            "creation_request_id", "creation_request_actor_id",
            "creation_request_fingerprint",
        )
        if any(
            getattr(customer_account, name) != getattr(persisted, name)
            for name in protected_fields
        ):
            raise ValueError("Account information updates must preserve account identity and associations.")

        editable_fields = {
            "display_name", "primary_contact_name", "primary_contact_email",
            "contact_telephone", "postal_address",
        }
        if persisted.account_type == "company":
            editable_fields.update({"company_name", "company_website"})
        elif persisted.account_type != "solo":
            raise ValueError("Account information updates require a solo or company account.")
        else:
            for name in ("company_name", "company_website"):
                if getattr(customer_account, name) != getattr(persisted, name):
                    raise ValueError("Company fields cannot be changed on a solo account.")

        additions, removals = Graph(), Graph()
        for name in sorted(editable_fields):
            value = getattr(customer_account, name)
            if not isinstance(value, str):
                raise ValueError(f"{name} must be text.")
            if value == getattr(persisted, name):
                continue
            predicate = self.TEXT_FIELDS[name]
            for triple in graph.triples((account, predicate, None)):
                removals.add(triple)
            additions.add((account, predicate, Literal(value, datatype=XSD.string)))

        if not additions and not removals:
            return
        # apply_change also writes affected-resource, actor, time, operation,
        # and shape-version provenance in the same validated transaction.
        # Preserve its validation, unavailable, and uncertain-outcome failures.
        self.store.apply_change(
            additions=additions, removals=removals, actor_id=str(actor),
            expected_versions={str(account): self.store._resource_version(graph, str(account))},
        )

    def add_membership(
        self, membership: CustomerAccountMembership, *, actor_id: str,
    ) -> None:
        """Add an explicit membership and attribution without replacing data.

        Authentication and admission are application prerequisites. Recheck
        account status and the acting owner's persisted authorization here.
        """
        actor = self._user_iri(actor_id)
        user = self._user_iri(membership.human_user_id)
        if not isinstance(membership.customer_account_id, str):
            raise ValueError("An existing customer-account ID is required.")
        account = _iri(membership.customer_account_id)
        if membership.active is not True:
            raise ValueError("A granted membership must be active.")
        try:
            role = CustomerAccountRole(membership.role)
        except (TypeError, ValueError) as error:
            raise ValueError("Choose a supported customer-account role.") from error

        graph = self.store.retrieve()
        persisted = self._account_from_graph(graph, str(account))
        owners = [
            member for member in persisted.memberships
            if member.active
            and member.role == CustomerAccountRole.OWNER
            and member.human_user_id == actor_id
            and member.customer_account_id == str(account)
        ]
        if not owners:
            raise PermissionError("An active owner in the same customer account is required.")
        if persisted.status != "active" or persisted.account_type != "company":
            raise ValueError("Membership grants require an active company account.")
        if any(
            member.human_user_id == membership.human_user_id
            and member.customer_account_id == str(account)
            and member.role == role
            for member in persisted.memberships
        ):
            raise ValueError("This user already has that role; manage the existing membership.")

        customer = self.CUSTOMER
        node = URIRef(f"urn:uad:customer-membership:{uuid4()}")
        additions = Graph()
        additions.add((user, RDF.type, customer.User))
        additions.add((node, RDF.type, customer.Membership))
        additions.add((node, customer.account, account))
        additions.add((node, customer.user, user))
        additions.add((
            node, customer.humanUserId,
            Literal(membership.human_user_id, datatype=XSD.string),
        ))
        additions.add((node, customer.role, self.ROLE_IRIS[role]))
        additions.add((node, customer.active, Literal(True)))

        # Guard the account and the persisted owner membership used above.
        # These are the existing store's version checks, not a claim that
        # simultaneous grants or authorization changes are serialized.
        guarded = {str(account)}
        for owner_node in graph.subjects(customer.account, account):
            if (
                (owner_node, RDF.type, customer.Membership) in graph
                and (owner_node, customer.user, actor) in graph
                and (owner_node, customer.role, customer.Owner) in graph
            ):
                guarded.add(str(owner_node))
        expected_versions = {
            resource: self.store._resource_version(graph, resource)
            for resource in guarded
        }
        # apply_change writes membership RDF and actor/time/shape attribution
        # atomically. Preserve its rejection and uncertain-outcome exceptions.
        self.store.apply_change(
            additions=additions, removals=Graph(), actor_id=str(actor),
            expected_versions=expected_versions,
        )

    def deactivate_membership(
        self, membership: CustomerAccountMembership, *, actor_id: str,
    ) -> None:
        """Deactivate one stored role without deleting identity or owned data."""
        actor = self._user_iri(actor_id)
        user = self._user_iri(membership.human_user_id)
        if not isinstance(membership.customer_account_id, str):
            raise ValueError("An existing customer-account ID is required.")
        account = _iri(membership.customer_account_id)
        try:
            role = CustomerAccountRole(membership.role)
        except (TypeError, ValueError) as error:
            raise ValueError("Choose a supported customer-account role.") from error
        graph = self.store.retrieve()
        persisted = self._account_from_graph(graph, str(account))
        if not any(
            member.active
            and member.role == CustomerAccountRole.OWNER
            and member.human_user_id == actor_id
            and member.customer_account_id == str(account)
            for member in persisted.memberships
        ):
            raise PermissionError("An active owner in the same customer account is required.")
        if persisted.status != "active" or persisted.account_type != "company":
            raise ValueError("Membership removal requires an active company account.")

        customer = self.CUSTOMER
        targets = [
            node for node in graph.subjects(customer.account, account)
            if (node, RDF.type, customer.Membership) in graph
            and (node, customer.user, user) in graph
            and (node, customer.role, self.ROLE_IRIS[role]) in graph
            and self._text(graph, node, customer.humanUserId) == membership.human_user_id
        ]
        if not targets:
            raise LookupError("The selected membership does not exist in this account.")
        if len(targets) != 1:
            raise RuntimeError("The selected user and role identify multiple memberships.")
        node = targets[0]
        if not self._boolean(graph, node, customer.active):
            return
        # Preserve the scenario prerequisite: an active owner must remain.
        remaining_owners = [
            member for member in persisted.memberships
            if member.active and member.role == CustomerAccountRole.OWNER
            and not (
                role == CustomerAccountRole.OWNER
                and member.human_user_id == membership.human_user_id
            )
        ]
        if not remaining_owners:
            raise ValueError("Another active owner must first be designated.")

        removals, additions = Graph(), Graph()
        for triple in graph.triples((node, customer.active, None)):
            removals.add(triple)
        additions.add((node, customer.active, Literal(False)))

        # Keep the existing resource-version checks for the account and its
        # memberships. These checks do not serialize simultaneous removals.
        guarded = {str(account)}
        guarded.update(
            str(candidate)
            for candidate in graph.subjects(customer.account, account)
            if (candidate, RDF.type, customer.Membership) in graph
        )
        expected_versions = {
            resource: self.store._resource_version(graph, resource)
            for resource in guarded
        }
        # The active flag and durable actor/time attribution commit together.
        # Validation, unavailable, and uncertain-outcome errors propagate.
        self.store.apply_change(
            additions=additions, removals=removals, actor_id=str(actor),
            expected_versions=expected_versions,
        )

    def change_membership_role(
        self, membership: CustomerAccountMembership, *,
        role: CustomerAccountRole, actor_id: str,
    ) -> None:
        """Change one persisted role and its attribution in one transaction."""
        actor = self._user_iri(actor_id)
        user = self._user_iri(membership.human_user_id)
        if not isinstance(membership.customer_account_id, str):
            raise ValueError("An existing customer-account ID is required.")
        account = _iri(membership.customer_account_id)
        try:
            old_role = CustomerAccountRole(membership.role)
            new_role = CustomerAccountRole(role)
        except (TypeError, ValueError) as error:
            raise ValueError("Choose a supported customer-account role.") from error

        graph = self.store.retrieve()
        persisted = self._account_from_graph(graph, str(account))
        if not any(
            member.active and member.role == CustomerAccountRole.OWNER
            and member.human_user_id == actor_id
            and member.customer_account_id == str(account)
            for member in persisted.memberships
        ):
            raise PermissionError("An active owner in the same customer account is required.")
        if persisted.status != "active" or persisted.account_type != "company":
            raise ValueError("Role changes require an active company account.")

        customer = self.CUSTOMER
        targets = [
            node for node in graph.subjects(customer.account, account)
            if (node, RDF.type, customer.Membership) in graph
            and (node, customer.user, user) in graph
            and (node, customer.role, self.ROLE_IRIS[old_role]) in graph
            and self._text(graph, node, customer.humanUserId) == membership.human_user_id
        ]
        if len(targets) != 1:
            raise ValueError("The selected membership must identify exactly one stored role.")
        node = targets[0]
        if not self._boolean(graph, node, customer.active):
            raise ValueError("Only an active membership can change roles.")
        if new_role == old_role:
            return
        if old_role == CustomerAccountRole.OWNER and not any(
            member.active and member.role == CustomerAccountRole.OWNER
            and member.customer_account_id == str(account)
            and member.human_user_id != membership.human_user_id
            for member in persisted.memberships
        ):
            raise ValueError("Another active owner must first be designated.")
        if any(
            member.human_user_id == membership.human_user_id
            and member.customer_account_id == str(account)
            and member.role == new_role
            for member in persisted.memberships
        ):
            raise ValueError("This user already has the requested role; manage that membership.")

        removals, additions = Graph(), Graph()
        for triple in graph.triples((node, customer.role, None)):
            removals.add(triple)
        additions.add((node, customer.role, self.ROLE_IRIS[new_role]))
        guarded = {str(account)}
        guarded.update(
            str(candidate)
            for candidate in graph.subjects(customer.account, account)
            if (candidate, RDF.type, customer.Membership) in graph
        )
        # Retain existing resource-version checks. They do not serialize
        # simultaneous role changes or owner removals.
        expected_versions = {
            resource: self.store._resource_version(graph, resource)
            for resource in guarded
        }
        # Only the role predicate changes. Identity, active status, account
        # ownership, credits, and validation work are left untouched.
        self.store.apply_change(
            additions=additions, removals=removals, actor_id=str(actor),
            expected_versions=expected_versions,
        )

    def close_account(
        self, *, customer_account_id: str, actor_id: str,
        expected_account: CustomerAccount,
    ) -> None:
        """Persist closure and attribution without deleting account history.

        The lifecycle service verifies explicit confirmation and obligations.
        Recheck stored ownership, lifecycle state and the supplied snapshot.
        """
        actor = self._user_iri(actor_id)
        account = _iri(customer_account_id)
        graph = self.store.retrieve()
        persisted = self._account_from_graph(graph, str(account))
        if not any(
            member.active and member.role == CustomerAccountRole.OWNER
            and member.human_user_id == actor_id
            and member.customer_account_id == str(account)
            for member in persisted.memberships
        ):
            raise PermissionError("An active owner in this customer account must complete closure.")
        if persisted.status != "active":
            raise ValueError("Only an active customer account can be closed.")
        if not isinstance(expected_account, CustomerAccount):
            raise TypeError("Supply the account snapshot checked for closure.")
        if expected_account.customer_account_id != str(account):
            raise ValueError("The expected snapshot must identify the same account.")
        if expected_account != persisted:
            raise StaleResourceVersionError(
                str(account),
                self._account_snapshot_version(expected_account),
                self._account_snapshot_version(persisted),
            )

        customer = self.CUSTOMER
        removals, additions = Graph(), Graph()
        for triple in graph.triples((account, customer.status, None)):
            removals.add(triple)
        additions.add((account, customer.status, Literal("closed", datatype=XSD.string)))
        guarded = {str(account)}
        guarded.update(
            str(node) for node in graph.subjects(customer.account, account)
            if (node, RDF.type, customer.Membership) in graph
        )
        # Existing version checks detect observed intervening changes; they do
        # not serialize purchases or validation work against account closure.
        expected_versions = {
            resource: self.store._resource_version(graph, resource)
            for resource in guarded
        }
        # apply_change atomically writes the status and actor/time attribution.
        # Preserve validation, unavailable, and uncertain-commit exceptions.
        self.store.apply_change(
            additions=additions, removals=removals, actor_id=str(actor),
            expected_versions=expected_versions,
        )

    def find_by_creation_request(self, *, actor_id: str, request_id: str) -> CustomerAccount | None:
        """Locate a completed request in this customer graph and actor scope."""
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("An identified request actor is required.")
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("A nonempty creation request ID is required.")
        graph = self.store.retrieve()
        customer = self.CUSTOMER
        matches = []
        for account in set(graph.subjects(RDF.type, customer.CustomerAccount)):
            stored_request = self._optional_text(graph, account, customer.creationRequestId)
            if stored_request != request_id:
                continue
            stored_actor = self._optional_text(graph, account, customer.creationRequestActorId)
            if stored_actor == actor_id:
                matches.append(account)
        if len(matches) > 1:
            raise RuntimeError("Multiple accounts are associated with the same actor and creation request.")
        if not matches:
            return None
        return self.get(str(matches[0]))

    def list_for_user(self, human_user_id: str) -> tuple[CustomerAccount, ...]:
        """Read accounts linked to this user's active, consistent memberships.

        Use one persisted graph snapshot for both authorization filtering and
        aggregate reconstruction. No account or audit records are written.
        """
        user_iri = self._user_iri(human_user_id)
        graph = self.store.retrieve()
        customer = self.CUSTOMER
        account_ids = set()
        for membership in set(graph.subjects(customer.user, user_iri)):
            if (membership, RDF.type, customer.Membership) not in graph:
                continue
            if self._text(graph, membership, customer.humanUserId) != human_user_id:
                continue
            if not self._boolean(graph, membership, customer.active):
                continue
            role = self._one(graph, membership, customer.role)
            if role not in self.ROLE_IRIS.values():
                raise RuntimeError("Unknown persisted customer-account role.")
            account = self._one(graph, membership, customer.account)
            if not isinstance(account, URIRef):
                raise RuntimeError("A stored membership must reference a customer-account IRI.")
            if (account, RDF.type, customer.CustomerAccount) not in graph:
                raise RuntimeError("An active membership references a missing customer account.")
            account_ids.add(str(account))
        return tuple(
            self._account_from_graph(graph, account_id)
            for account_id in sorted(account_ids)
        )

    def get(self, customer_account_id: str) -> CustomerAccount:
        account = _iri(customer_account_id)
        return self._account_from_graph(self.store.retrieve(), str(account))

    def _account_from_graph(self, graph: Graph, customer_account_id: str) -> CustomerAccount:
        account = _iri(customer_account_id)
        customer = self.CUSTOMER
        if (account, RDF.type, customer.CustomerAccount) not in graph:
            raise KeyError(customer_account_id)
        values = {
            field_name: self._text(graph, account, predicate)
            for field_name, predicate in self.TEXT_FIELDS.items()
        }
        values.update({
            name: self._optional_text(graph, account, predicate)
            for name, predicate in self.REQUEST_FIELDS.items()
        })
        timestamp = self._one(graph, account, customer.createdAt)
        created_at = timestamp.toPython() if isinstance(timestamp, Literal) else None
        if not isinstance(created_at, datetime) or created_at.utcoffset() is None:
            raise RuntimeError("Invalid persisted customer-account creation time.")
        roles = {iri: role for role, iri in self.ROLE_IRIS.items()}
        memberships = []
        for node in sorted(set(graph.subjects(customer.account, account)), key=str):
            if (node, RDF.type, customer.Membership) not in graph:
                continue
            role_iri = self._one(graph, node, customer.role)
            if role_iri not in roles:
                raise RuntimeError("Unknown persisted customer-account role.")
            human_user_id = self._text(graph, node, customer.humanUserId)
            if self._one(graph, node, customer.user) != self._user_iri(human_user_id):
                raise RuntimeError("Stored membership user identity is inconsistent.")
            memberships.append(CustomerAccountMembership(
                human_user_id=human_user_id,
                role=roles[role_iri],
                active=self._boolean(graph, node, customer.active),
                customer_account_id=str(account),
            ))
        return CustomerAccount(
            customer_account_id=str(account),
            is_ownership_boundary=self._boolean(graph, account, customer.isOwnershipBoundary),
            is_billing_boundary=self._boolean(graph, account, customer.isBillingBoundary),
            memberships=tuple(memberships),
            created_at=created_at,
            **values,
        )



