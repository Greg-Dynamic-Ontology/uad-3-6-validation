"""Generate schema-valid, reusable IT-1R11S1 XML fixtures and manifest.ttl.

Default: build and validate in memory, then verify any saved corpus.
Write only with --write. Replacement additionally requires --replace-generated
and matching hashes in the previous manifest. No production files are changed.
"""

import argparse
import csv
import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path, PurePosixPath

from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = "tests/fixtures/it_1/r11/s1"
GENERATOR = "scripts/testing/generate_it_1_r11_s1_fixtures.py"
SOURCE = (
    "chatgpt-sources/sources/samples/UAD/"
    "Appendix D-1 URAR Sample Use Cases and XML Files/"
    "Appendix D-1 SF1_Appraisal/SF1_Appraisal_v1.4.xml"
)
SOURCE_SHA256 = "47509c23bcf28c3abb9c57e00a3f93cf52ed38fec3862d7cda24bffd6bca5be9"
SCHEMA = (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
TRACKING = "data/spreadsheet-rule-category-tracking.ttl"
CSV = "data/data-constraints.csv"
EVALUATION_DATE = date(2026, 10, 2)
EFFECTIVE_DATE = "2019-09-20"
AGE_LIMIT = (EVALUATION_DATE - timedelta(days=367)).isoformat()
TOO_OLD = (EVALUATION_DATE - timedelta(days=368)).isoformat()
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:date-chronology")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:date_chronology")
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
    "xs": "http://www.w3.org/2001/XMLSchema",
}
M = "{" + NS["m"] + "}"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
FIELDS = {
    "Message ID": T.ruleId,
    "Unique ID": T.sourceUniqueIdCell,
    "Primary Data Element": T.primaryDataElement,
    "Rule Logic": T.ruleLogic,
    "Severity": T.severity,
    "Property Affected": T.propertyAffected,
    " xPath": T.xpath,
    "Message Text": T.messageText,
}
FINGERPRINTS = {
    "UAD1051": "3b3ca5c75743d6446c9b040efb82113bcb847ab91ee88bf4b49b6af1b91bab67",
    "UAD1053": "b468bc3be2946c82aee64972d55b746eab9477b87298bc4e35d20853ffcee07b",
    "UAD1131": "854b7de4a16591693f782f8b9d9d9c9d1748e4f7cec63ccb84ebc5ae00f79ae3",
    "UAD1206": "4ecb705407477878c1ad4d9bf82af6d98d0248be95330cbe67ede4f75b2361f3",
    "UAD1258": "27a11458158e9f7576b24549252ce2903d0a8aa5065c7d8c7f10b24a57da66f9",
    "UAD1259": "8923eb6ceb9331e1bc5ac8d805433d261fddae60faad035d69714383951950c0",
    "UAD1505": "d3217926bb300c670cfe1bce5263368970c24e2f550f746427a8c062f7429378",
    "UAD1506": "227c2483031da37ffd05aea87d6f059b87aeadad9fdb047d215fc0b24b68c447",
    "UAD1529": "e29a6e63200d475c3166fd6e8b4586dcdfeedd84b4a7f30bdc9fdb46355a1ed8",
    "UAD1536": "55cb501f9bde4d0f1bbb05eaa02fee04fb923464a0aea2abcdc76e3933a41175",
    "UAD1557": "6366f4eaed7edaaf90f7659a45877bfb1b1fcba629a57cbbd0a43600bb34b6d3",
    "UAD1611": "ba015cf73a70baee263ad42d91277343e4197e4ccd4e5c4572d491e2d998be05",
    "UAD1756": "f04e49a81f3b438e5eafec77f87c573448bc2e412dd9bc4b32ece22e0ac745e1",
    "UAD1757": "e8edf2dc0ec2eb0523a3e072f67806578ea5bdb3caf3ab80457ba6e05494d54a",
}


@dataclass(frozen=True)
class Plan:
    rule_id: str
    name: str
    good: str
    changed: str
    mode: str = ""
    expected: int = 1


PLANS = (
    Plan("UAD1051", "previous-year-boundary", "2018", "2017"),
    Plan("UAD1051", "same-year", "2019", "2021"),
    Plan("UAD1051", "following-year-boundary", "2020", "2021"),
    Plan("UAD1051", "not-new-construction-control", "2019", "2010",
         "not-new", 0),
    Plan("UAD1051", "outbuilding-control", "2019", "2010",
         "outbuilding", 0),
    Plan("UAD1053", "c1-two-year-boundary", "2021", "2022", "C1"),
    Plan("UAD1053", "non-c1-effective-year-boundary", "2019", "2020", "C4"),
    Plan("UAD1053", "outbuilding-control", "2019", "2022", "outbuilding", 0),
    Plan("UAD1131", "equal-effective-date", EFFECTIVE_DATE, "2019-09-21"),
    Plan("UAD1131", "other-property-contract-context", EFFECTIVE_DATE,
         "2019-09-21", "repeated"),
    Plan("UAD1206", "equal-listing-dates", "2019-09-17", "2019-09-18"),
    Plan("UAD1206", "repeated-listing-context", "2019-09-17", "2019-09-18",
         "repeated"),
    Plan("UAD1258", "today-boundary", EVALUATION_DATE.isoformat(), "2026-10-03"),
    Plan("UAD1259", "367-day-boundary", AGE_LIMIT, TOO_OLD),
    Plan("UAD1505", "today-boundary", EVALUATION_DATE.isoformat(), "2026-10-03"),
    Plan("UAD1506", "367-day-boundary", AGE_LIMIT, TOO_OLD),
    Plan("UAD1529", "appraiser-equal-effective-date",
         EFFECTIVE_DATE, "2019-09-19", "Appraiser"),
    Plan("UAD1529", "supervisor-equal-effective-date",
         EFFECTIVE_DATE, "2019-09-19", "AppraiserSupervisor"),
    Plan("UAD1529", "other-role-control",
         EFFECTIVE_DATE, "2019-09-19", "Borrower", 0),
    Plan("UAD1536", "equal-effective-date", EFFECTIVE_DATE, "2019-09-19"),
    Plan("UAD1557", "equal-effective-date", EFFECTIVE_DATE, "2019-09-21"),
    Plan("UAD1611", "equal-effective-month", "2019-09", "2019-08"),
    Plan("UAD1611", "same-month-earlier-day", "2019-09-01", "2019-08-31"),
    Plan("UAD1756", "equal-effective-date", EFFECTIVE_DATE, "2019-09-19"),
    Plan("UAD1757", "367-day-boundary", AGE_LIMIT, TOO_OLD),
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(row):
    return sha256(json.dumps(
        [row[key] for key in FIELDS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8"))


def one(node, xpath):
    selected = node.xpath(xpath, namespaces=NS)
    if len(selected) != 1:
        raise ValueError(
            f"Expected exactly one node for {xpath}: {len(selected)}"
        )
    return selected[0]


def absolute_path(node):
    parts = []
    while node is not None:
        name = "m:" + etree.QName(node).localname
        parent = node.getparent()
        if parent is not None:
            siblings = [item for item in parent if item.tag == node.tag]
            if len(siblings) > 1:
                name += f"[{siblings.index(node) + 1}]"
        parts.append(name)
        node = parent
    return "/" + "/".join(reversed(parts))


def set_text(node, value, changes):
    before = node.text or ""
    if before != value:
        changes.append((absolute_path(node), before, value))
        node.text = value


def ensure_child(parent, name, schema_document, additions):
    matches = parent.findall(M + name)
    if matches:
        if len(matches) != 1:
            raise ValueError(f"Ambiguous existing {name}")
        return matches[0]
    type_name = etree.QName(parent).localname
    declarations = schema_document.xpath(
        "/xs:schema/xs:complexType[@name=$name]/xs:sequence/xs:element",
        namespaces=NS, name=type_name,
    )
    order = [item.get("name") for item in declarations]
    if name not in order:
        raise ValueError(
            f"No direct schema sequence entry for {type_name}/{name}"
        )
    rank = order.index(name)
    child = etree.Element(M + name)
    index = len(parent)
    for position, sibling in enumerate(parent):
        sibling_name = etree.QName(sibling).localname
        if sibling_name in order and order.index(sibling_name) > rank:
            index = position
            break
    parent.insert(index, child)
    additions.append(absolute_path(child))
    return child


def source_rows():
    tracking = Graph().parse(ROOT / TRACKING, format="turtle")
    governed = {
        str(tracking.value(node, WT.ruleId)): node
        for node in tracking.objects(SCENARIO, WT.coversRule)
    }
    if set(governed) != set(FINGERPRINTS):
        raise ValueError(
            "Governed chronology membership differs from reviewed 14 rows"
        )
    with (ROOT / CSV).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = {}
    for rule_id, expected_hash in FINGERPRINTS.items():
        matches = [row for row in rows if row["Message ID"] == rule_id]
        if len(matches) != 1:
            raise ValueError(f"{rule_id}: expected one original CSV row")
        row = matches[0]
        if fingerprint(row) != expected_hash:
            raise ValueError(f"{rule_id}: reviewed CSV definition changed")
        for column, predicate in FIELDS.items():
            key = str(predicate).removeprefix(str(T))
            values = list(tracking.objects(governed[rule_id], WT[key]))
            if len(values) != 1 or str(values[0]) != row[column]:
                raise ValueError(
                    f"{rule_id}: CSV/tracking mismatch for {column}"
                )
        selected[rule_id] = (row, governed[rule_id])
    return selected


def prepare(plan, original, schema_document):
    root = etree.fromstring(original, etree.XMLParser(
        resolve_entities=False, no_network=True, remove_blank_text=True,
    ))
    changes, additions = [], []
    analysis = one(root, "//m:VALUATION_ANALYSIS")
    subject = one(
        analysis,
        "m:PROPERTIES/m:PROPERTY[@ValuationUseType='SubjectProperty']",
    )
    effective = one(
        analysis, "m:VALUATION_REPORT/m:VALUATION_RECONCILIATION/"
        "m:VALUATION_RECONCILIATION_SUMMARY/"
        "m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:AppraisalReportEffectiveDate",
    )
    set_text(effective, EFFECTIVE_DATE, changes)
    reference = effective
    applicability = "true()"
    rule_id = plan.rule_id

    if rule_id in {"UAD1051", "UAD1053"}:
        detail = one(subject, "m:PROPERTY_DETAIL")
        trigger = one(detail, "m:NewConstructionIndicator")
        set_text(
            trigger, "false" if plan.mode == "not-new" else "true", changes,
        )
        improvement = one(subject, "m:IMPROVEMENTS/m:IMPROVEMENT[1]")
        imp_detail = one(improvement, "m:IMPROVEMENT_DETAIL")
        kind = one(imp_detail, "m:ImprovementType")
        set_text(
            kind, "Outbuilding" if plan.mode == "outbuilding" else "Dwelling",
            changes,
        )
        target = one(imp_detail, "m:PropertyStructureBuiltYear")
        rating = one(
            improvement,
            "m:STRUCTURE/m:STRUCTURE_DETAIL/m:ExteriorConditionRatingCode",
        )
        set_text(rating, "C1" if plan.mode == "C1" else "C4", changes)
        applicability = f"({absolute_path(kind)} = 'Dwelling')"
        if rule_id == "UAD1051":
            applicability += f" and ({absolute_path(trigger)} = 'true')"
    elif rule_id == "UAD1131":
        contract = one(subject, "m:SALES_CONTRACTS/m:SALES_CONTRACT[1]")
        if plan.mode == "repeated":
            other_property = one(analysis, "m:PROPERTIES/m:PROPERTY[2]")
            other_contracts = ensure_child(
                other_property, "SALES_CONTRACTS", schema_document, additions,
            )
            other_contract = ensure_child(
                other_contracts, "SALES_CONTRACT", schema_document, additions,
            )
            other_detail = ensure_child(
                other_contract, "SALES_CONTRACT_DETAIL",
                schema_document, additions,
            )
            other_date = ensure_child(
                other_detail, "SalesContractDate", schema_document, additions,
            )
            set_text(other_date, "2019-10-01", changes)
        target = one(contract, "m:SALES_CONTRACT_DETAIL/m:SalesContractDate")
    elif rule_id == "UAD1206":
        listing = one(
            subject, "m:LISTING_INFORMATIONS/m:LISTING_INFORMATION[1]",
        )
        if plan.mode == "repeated":
            extra = deepcopy(listing)
            for element in extra.iter():
                element.attrib.pop("{" + NS["xlink"] + "}label", None)
                element.attrib.pop("SequenceNumber", None)
            one(
                extra, "m:LISTING_INFORMATION_DETAIL/m:ListingStartDate",
            ).text = "2019-01-01"
            one(
                extra, "m:LISTING_INFORMATION_DETAIL/m:ListingEndDate",
            ).text = "2019-12-31"
            listing.getparent().append(extra)
            additions.append(absolute_path(extra))
        target = one(
            listing, "m:LISTING_INFORMATION_DETAIL/m:ListingStartDate",
        )
        reference = one(
            listing, "m:LISTING_INFORMATION_DETAIL/m:ListingEndDate",
        )
    elif rule_id in {"UAD1258", "UAD1259"}:
        target = effective
        reference = None
    elif rule_id in {"UAD1505", "UAD1506", "UAD1536"}:
        target = one(
            root, "//m:SIGNATORY/m:EXECUTION/m:EXECUTION_DETAIL/m:ExecutionDate",
        )
        if rule_id != "UAD1536":
            reference = None
    elif rule_id == "UAD1529":
        role = one(
            root, "//m:ROLE[m:ROLE_DETAIL/m:PartyRoleType='Appraiser']",
        )
        role_type = one(role, "m:ROLE_DETAIL/m:PartyRoleType")
        set_text(role_type, plan.mode, changes)
        target = one(
            role,
            "m:LICENSES/m:LICENSE/m:LICENSE_DETAIL/m:LicenseExpirationDate",
        )
        applicability = (
            f"({absolute_path(role_type)} = 'Appraiser') or "
            f"({absolute_path(role_type)} = 'AppraiserSupervisor')"
        )
    elif rule_id == "UAD1557":
        target = one(
            subject,
            "m:INSPECTIONS/m:INSPECTION/m:INSPECTION_DETAIL/m:InspectionDate",
        )
    elif rule_id == "UAD1611":
        tax = one(subject, "m:PROPERTY_TAXES/m:PROPERTY_TAX[1]")
        indicator = one(
            tax,
            "m:PROPERTY_TAX_DETAIL/m:PropertyTaxAbatementsOrExemptionsIndicator",
        )
        set_text(indicator, "true", changes)
        exemptions = ensure_child(
            tax, "PROPERTY_TAX_EXEMPTIONS", schema_document, additions,
        )
        exemption = ensure_child(
            exemptions, "PROPERTY_TAX_EXEMPTION", schema_document, additions,
        )
        target = ensure_child(
            exemption, "TaxAbatementsOrExemptionsExpirationDate",
            schema_document, additions,
        )
    elif rule_id in {"UAD1756", "UAD1757"}:
        report = one(analysis, "m:VALUATION_REPORT")
        rovs = ensure_child(
            report, "RECONSIDERATIONS_OF_VALUE", schema_document, additions,
        )
        rov = ensure_child(
            rovs, "RECONSIDERATION_OF_VALUE", schema_document, additions,
        )
        target = ensure_child(
            rov, "ReconsiderationOfValueResultDate",
            schema_document, additions,
        )
        if rule_id == "UAD1757":
            reference = None
    else:
        raise ValueError(f"Unsupported test recipe: {rule_id}")

    set_text(target, plan.good, changes)
    return root, target, reference, applicability, changes, additions


def serialize_xml(root, relative, schema):
    schema_reference = Path(os.path.relpath(
        ROOT / SCHEMA, (ROOT / relative).parent,
    )).as_posix()
    root.set(
        "{" + XSI + "}schemaLocation",
        NS["m"] + " " + schema_reference,
    )
    etree.cleanup_namespaces(root, top_nsmap={"xsi": XSI})
    data = etree.tostring(
        root, encoding="UTF-8", xml_declaration=True, pretty_print=True,
    )
    reparsed = etree.fromstring(
        data, etree.XMLParser(resolve_entities=False, no_network=True),
    )
    schema.assertValid(reparsed)
    return data


def build():
    rows = source_rows()
    original = (ROOT / SOURCE).read_bytes()
    if sha256(original) != SOURCE_SHA256:
        raise ValueError(
            "Published SF1 source bytes differ from reviewed source"
        )
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema_document = etree.parse(str(ROOT / SCHEMA), parser)
    schema = etree.XMLSchema(schema_document)
    schema.assertValid(etree.fromstring(original, parser))
    if {plan.rule_id for plan in PLANS} != set(FINGERPRINTS):
        raise ValueError("Test plans do not cover all reviewed chronology rows")

    graph = Graph()
    graph.bind("t", T)
    graph.bind("wt", WT)
    graph.add((SUITE, RDF.type, T.TestSuite))
    for name, value in {
        "scenarioId": "IT-1R11S1",
        "generatedBy": GENERATOR,
        "expectedCaseCount": len(PLANS),
        "expectedFixtureCount": len(PLANS) * 2,
        "sourceRuleCount": len(FINGERPRINTS),
        "evaluationDate": EVALUATION_DATE.isoformat(),
        "publishedSourcePath": SOURCE,
        "publishedSourceSha256": SOURCE_SHA256,
        "schemaPath": SCHEMA,
        "schemaSha256": sha256((ROOT / SCHEMA).read_bytes()),
        "note": (
            "Schema-valid chronology fixtures derived from published SF1 XML. "
            "Expectations apply to the selected original CSV row only. Other "
            "business-rule findings may occur. Clock-dependent endpoint replay "
            "requires the recorded evaluation date."
        ),
    }.items():
        graph.add((SUITE, T[name], Literal(value)))

    for path in sorted((ROOT / SCHEMA).parent.glob("*.xsd")):
        node = URIRef(str(SUITE) + ":schema:" + path.name)
        graph.add((SUITE, T.schemaSource, node))
        graph.add((node, T.path, Literal(path.relative_to(ROOT).as_posix())))
        graph.add((node, T.sha256, Literal(sha256(path.read_bytes()))))

    outputs = {}
    for plan in PLANS:
        case = URIRef(str(SUITE) + ":" + plan.rule_id + ":" + plan.name)
        row, governed = rows[plan.rule_id]
        graph.add((SUITE, T.hasCase, case))
        graph.add((case, RDF.type, T.TestCase))
        graph.add((case, T.sourceRule, governed))
        for column, predicate in FIELDS.items():
            graph.add((case, predicate, Literal(row[column])))

        root, target, reference, applicability, changes, additions = prepare(
            plan, original, schema_document,
        )
        target_path = absolute_path(target)
        for name, value in {
            "caseId": plan.name,
            "scenarioId": "IT-1R11S1",
            "sourceFingerprint": fingerprint(row),
            "targetXPath": target_path,
            "targetElement": etree.QName(target).localname,
            "baselineValue": plan.good,
            "changedValue": plan.changed,
            "applicabilityXPath": applicability,
            "expectedApplicable": plan.expected == 1,
            "evaluationDate": EVALUATION_DATE.isoformat(),
            "comparisonPrecision": (
                "year" if plan.rule_id in {"UAD1051", "UAD1053"} else
                "year-month" if plan.rule_id == "UAD1611" else "date"
            ),
            "referenceXPath": (
                "" if reference is None else absolute_path(reference)
            ),
            "referenceValue": (
                EVALUATION_DATE.isoformat()
                if reference is None else reference.text
            ),
        }.items():
            graph.add((case, T[name], Literal(value)))

        for number, (xpath, before, after) in enumerate(changes):
            node = URIRef(str(case) + f":setup:{number}")
            graph.add((case, T.setupChange, node))
            for name, value in {
                "xpath": xpath,
                "beforeValue": before,
                "afterValue": after,
            }.items():
                graph.add((node, T[name], Literal(value)))
        for xpath in additions:
            graph.add((case, T.addedContextXPath, Literal(xpath)))

        for state, raw, count in (
            ("permitted", plan.good, 0),
            (
                "prohibited" if plan.expected else "changed-control",
                plan.changed,
                plan.expected,
            ),
        ):
            target.text = raw
            relative = f"{FIXTURES}/{plan.rule_id}/{plan.name}-{state}.xml"
            data = serialize_xml(root, relative, schema)
            node = URIRef(str(case) + ":" + state)
            graph.add((case, T.hasFixture, node))
            graph.add((node, RDF.type, T.XMLFixture))
            for name, value in {
                "state": state,
                "path": relative,
                "sha256": sha256(data),
                "targetValue": raw,
                "expectedFindingCount": count,
                "expectedViolationKind": "ProhibitedDateRelationship",
                "xsdValid": True,
            }.items():
                graph.add((node, T[name], Literal(value)))
            if bool(root.xpath(applicability, namespaces=NS)) != (
                plan.expected == 1
            ):
                raise ValueError(
                    f"{plan.rule_id}/{plan.name}: applicability mismatch"
                )
            outputs[relative] = data

    manifest = graph.serialize(format="turtle").encode("utf-8")
    round_trip = Graph().parse(
        data=manifest.decode("utf-8"), format="turtle",
    )
    if not isomorphic(graph, round_trip):
        raise ValueError("Manifest Turtle round-trip changed the graph")
    outputs[FIXTURES + "/manifest.ttl"] = manifest
    return outputs, graph


def safe_path(relative):
    portable = PurePosixPath(relative)
    if (
        portable.is_absolute()
        or ".." in portable.parts
        or "\\" in relative
    ):
        raise ValueError(f"Unsafe output path: {relative}")
    path = (ROOT / portable).resolve()
    if not path.is_relative_to((ROOT / FIXTURES).resolve()):
        raise ValueError(f"Output escapes fixture directory: {relative}")
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Output escapes project: {relative}")
    return path


def existing_manifest():
    path = ROOT / FIXTURES / "manifest.ttl"
    if not path.is_file():
        return None
    graph = Graph().parse(path, format="turtle")
    if str(graph.value(SUITE, T.generatedBy)) != GENERATOR:
        raise ValueError("Existing manifest does not identify this generator")
    return graph


def verify_saved(outputs, graph):
    directory = ROOT / FIXTURES
    if not directory.exists():
        print(
            "No saved corpus yet; plan validated in memory. No files written."
        )
        return
    old = existing_manifest()
    if old is None:
        raise ValueError("Fixture directory exists without its manifest")
    actual_xml = {
        path.relative_to(ROOT).as_posix()
        for path in directory.rglob("*.xml")
    }
    expected_xml = {name for name in outputs if name.endswith(".xml")}
    if actual_xml != expected_xml:
        raise ValueError(
            "Saved XML membership differs from generated corpus"
        )
    for relative, data in outputs.items():
        path = safe_path(relative)
        if not path.is_file():
            raise ValueError(f"Missing saved artifact: {relative}")
        if relative.endswith(".xml") and path.read_bytes() != data:
            raise ValueError(
                f"Saved XML differs from generator: {relative}"
            )
    if not isomorphic(old, graph):
        raise ValueError("Saved manifest differs from generated knowledge")
    print("Saved XML bytes and manifest graph match the generator.")


def write(outputs, replace):
    old = existing_manifest()
    owned = {}
    if old is not None:
        for fixture in old.subjects(RDF.type, T.XMLFixture):
            paths = list(old.objects(fixture, T.path))
            hashes = list(old.objects(fixture, T.sha256))
            if len(paths) != 1 or len(hashes) != 1:
                raise ValueError(
                    "Existing manifest has ambiguous fixture ownership"
                )
            relative = str(paths[0])
            if relative in owned:
                raise ValueError(
                    "Existing manifest contains a duplicate fixture path"
                )
            path = safe_path(relative)
            if (
                not path.is_file()
                or sha256(path.read_bytes()) != str(hashes[0])
            ):
                raise ValueError(
                    f"Existing fixture was changed or is missing: {relative}"
                )
            owned[relative] = str(hashes[0])

    expected_xml = {name for name in outputs if name.endswith(".xml")}
    existing_xml = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / FIXTURES).rglob("*.xml")
    }
    if existing_xml and existing_xml != set(owned):
        raise ValueError("Unowned XML files exist; replacement refused")
    if old is not None and set(owned) != expected_xml:
        raise ValueError(
            "Fixture membership changed; review before replacing corpus"
        )

    # Preflight every output before writing any file.
    for relative, data in outputs.items():
        path = safe_path(relative)
        if path.exists() and path.read_bytes() != data:
            manifest_path = FIXTURES + "/manifest.ttl"
            if (
                not replace
                or old is None
                or (
                    relative != manifest_path
                    and relative not in owned
                )
            ):
                raise ValueError(f"Refusing overwrite: {relative}")

    for relative, data in outputs.items():
        path = safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    print(
        f"Wrote {len(outputs) - 1} schema-valid XML fixtures and manifest.ttl."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    if args.replace_generated and not args.write:
        parser.error("--replace-generated requires --write")
    outputs, graph = build()
    print(
        f"Validated {len(PLANS)} case pairs "
        f"for {len(FINGERPRINTS)} source rules."
    )
    if args.write:
        write(outputs, args.replace_generated)
    else:
        verify_saved(outputs, graph)


if __name__ == "__main__":
    main()