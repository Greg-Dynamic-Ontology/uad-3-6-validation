"""Evaluate reviewed equality bindings, independently of test definitions.

The production RDF identifies exact scope, dependent, and trigger paths. A
fingerprint pins each mapping to its governed CSV definition. Nothing here
reads test cases, fixtures, or expected findings.
"""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding

NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": NAMESPACE}
NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
B = Namespace("urn:uad36:single-equality-binding:")
BINDINGS = Path(__file__).resolve().parents[2] / "data/single-equality-bindings.ttl"
SOURCE_COLUMNS = (
    "Unique ID", "Message ID", "Primary Data Element", "Rule Logic",
    "Severity", "Property Affected", " xPath", "Message Text",
)


def fingerprint(row):
    return hashlib.sha256(json.dumps(
        [row.get(key) for key in SOURCE_COLUMNS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_bindings():
    graph = Graph().parse(BINDINGS, format="turtle")
    bindings = {}
    for node in graph.subjects(RDF.type, B.Binding):
        record = {}
        for name in (
            "ruleId", "sourceFingerprint", "scope", "property_type", "parent",
            "anchor", "trigger", "value", "element", "per_instance",
        ):
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = values[0].toPython()
        if record["ruleId"] in bindings:
            raise ValueError(f"Duplicate equality binding: {record['ruleId']}")
        if not isinstance(record["per_instance"], bool):
            raise ValueError(f"{node}: per_instance must be boolean")
        bindings[record["ruleId"]] = record
    return bindings


def binding_for(row):
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(f"{row.get('Message ID')}: governed equality definition changed")
    return record


def _lookup(path):
    return "/".join("m:" + part for part in path.split("/") if part)


def _has_value(node):
    return node.get(NIL) not in {"true", "1"} and bool((node.text or "").strip())


def _absolute(node, parents):
    parts = []
    while node is not None:
        name = "m:" + node.tag.removeprefix("{" + NAMESPACE + "}")
        parent = parents.get(node)
        if parent is not None:
            siblings = [child for child in parent if child.tag == node.tag]
            if len(siblings) > 1:
                name += f"[{siblings.index(node) + 1}]"
        parts.append(name)
        node = parent
    return "/" + "/".join(reversed(parts))


def _contexts(node, parts, ancestors):
    """Keep the ancestry of each occurrence, including absent singleton paths."""
    if not parts:
        yield node, ancestors, ()
        return
    children = node.findall("m:" + parts[0], NS)
    if not children:
        yield None, ancestors, tuple(parts)
    else:
        for child in children:
            yield from _contexts(child, parts[1:], ancestors + [child])


def evaluate_single_equality(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []
    parents = {child: parent for parent in root.iter() for child in parent}
    scopes = root.findall(".//" + _lookup(record["scope"]), NS)
    if root.tag == "{" + NAMESPACE + "}" + record["scope"].split("/")[0]:
        scopes = root.findall(_lookup("/".join(record["scope"].split("/")[1:])), NS) if "/" in record["scope"] else [root]
    findings = []
    for scope in scopes:
        if record["property_type"] and scope.get("ValuationUseType") != record["property_type"]:
            continue
        for container, ancestors, missing in _contexts(scope, record["parent"].split("/"), [scope]):
            if container is None and record["per_instance"]:
                continue
            elements = container.findall("m:" + record["element"], NS) if container is not None else []
            if elements and all(_has_value(element) for element in elements):
                continue
            depth = len(record["anchor"].split("/")) if record["anchor"] else 0
            anchor = ancestors[depth] if depth < len(ancestors) else None
            if anchor is None:
                continue
            if record["trigger"].startswith("@"):
                matches = [anchor.get(record["trigger"][1:])]
            else:
                triggers = anchor.findall(_lookup(record["trigger"]), NS)
                if any(list(node) for node in triggers):
                    raise ValueError(f"{row['Message ID']}: nonscalar equality input")
                # A party may hold multiple roles. Name requirements apply if
                # that same party holds the governed role. Other paths are
                # singular within the explicitly selected occurrence.
                if len(triggers) > 1 and row["Message ID"] not in {"UAD1561", "UAD1562"}:
                    raise ValueError(f"{row['Message ID']}: ambiguous equality input")
                matches = [(node.text or "").strip() for node in triggers if _has_value(node)]
            if record["value"] not in matches:
                continue
            existing = container if container is not None else ancestors[-1]
            location = _absolute(existing, parents)
            if missing:
                location += "/" + _lookup("/".join(missing))
            location += "/m:" + record["element"]
            findings.append(Finding(
                finding_id=f"F-{uuid4().hex[:8]}", severity=Severity(row["Severity"].casefold()),
                investor=investor, rule_type=RuleType.APPENDIX_H,
                rule_id=row["Message ID"], row_id=row["Unique ID"],
                primary_data_element=record["element"], property_affected=row["Property Affected"],
                violation_kind="MissingRequiredValue", data_location=location,
                nearest_existing_ancestor=_absolute(existing, parents) if not elements else None,
                observed_value="missing, empty, or nil", expected_condition=row["Rule Logic"],
                source=Provenance(source_document="data/data-constraints.csv", source_version="UAD 3.6", source_section=row["Unique ID"]),
                finding=row["Message Text"],
            ))
    return findings