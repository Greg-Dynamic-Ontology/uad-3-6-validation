# IT-1R1 / IT-1R1S1 — Slice 02 Test Summary

## Status

**Planned — this slice’s fixtures and tests have not been
constructed or executed.**

This document defines the intended coverage and construction
process. It does not record observed RED or GREEN results.

## Behavior and scope

**Iteration:** IT-1  
**Rule:** IT-1R1 — Other conditional or scoped requirements follow
their governed applicability  
**Scenario:** IT-1R1S1 — Enforce a requirement in its
applicable condition and scope  
**Slice:** 02 — 30 additional source rules

The authoritative behavior remains in:

`features/spreadsheet-rule-category-validation.feature`

The selected membership is recorded in:

`data/spreadsheet-rule-category-tracking.ttl`

Selection resource:

`urn:uad36:work-tracking:r1-classification:nextSlice`

Selection predicate:

`urn:uad36:work-tracking:vocab:proposedSliceRule`

The slice contains 17 rules classified as
`repeated-local-scalar` and 13 as `repeated-local-compound`.
These are internal implementation classifications.
Source rule logic, source identifiers, severity, and scope
remain authoritative.

The shared behavior is instance-local evaluation: a condition
and its required dependent data belong to the same repeated
XML context.
Data or conditions in another instance must not satisfy or
activate this instance’s requirement.

The prior slice covered UAD1021, UAD1024, and UAD1054.
Completing this slice would bring coverage to 33 of the
category’s 228 source rules, leaving 195.
That accounting does not establish completion until the new
tests pass and regression evidence is recorded.

## Selected source rules

The following table summarizes coverage.
Exact source wording and XPath remain in the TTL.

| Rule ID | Severity | Applicability and required data                                                                                                                               |
|---------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| UAD1094 | Fatal    | Outbuilding with real-property indicator true requires OutbuildingDefectsExistIndicator.                                                                      |
| UAD1100 | Warning  | Financing eligibility identifier present requires eligibility type.                                                                                           |
| UAD1101 | Warning  | Financing eligibility type present requires eligibility identifier.                                                                                           |
| UAD1147 | Fatal    | FullBathroom, HalfBathroom, or Kitchen with FullyUpdated or PartiallyUpdated status requires RoomUpdatedTimeframeType.                                        |
| UAD1156 | Fatal    | WallsAndCeiling or Other interior component requires ImprovementComponentConditionStatusType.                                                                 |
| UAD1294 | Warning  | Environmental condition other than None, with Bordering or Offsite proximity, requires DistanceFromPropertyLinearMeasure.                                     |
| UAD1298 | Fatal    | Environmental condition other than None requires EnvironmentalConditionProximityType.                                                                         |
| UAD1330 | Warning  | Site influence other than BodyOfWater requires SiteInfluenceProximityType.                                                                                    |
| UAD1556 | Fatal    | Physical or Virtual exterior or interior inspection requires InspectionDate.                                                                                  |
| UAD1568 | Fatal    | BoatSlip or UnitStorage amenity requires AmenityOwnershipType.                                                                                                |
| UAD1573 | Fatal    | AssociationDues charge requires AssociationChargeAmount.                                                                                                      |
| UAD1578 | Fatal    | Existing AssociationSpecialAssessment requires AssociationChargeBalanceAmount.                                                                                |
| UAD1613 | Fatal    | AssociationSpecialAssessment requires AssociationSpecialAssessmentStatusType.                                                                                 |
| UAD1629 | Fatal    | ActiveListings inventory requires MarketInventoryCount.                                                                                                       |
| UAD1630 | Fatal    | ActiveListings inventory with count greater than zero requires MarketInventoryHighestPriceAmount.                                                             |
| UAD1632 | Fatal    | ActiveListings inventory with count greater than zero requires MarketInventoryLowestPriceAmount.                                                              |
| UAD1634 | Fatal    | ActiveListings inventory with count greater than zero requires MarketInventoryMedianDaysOnMarketCount.                                                        |
| UAD1635 | Warning  | ActiveListings inventory with count greater than zero requires MarketInventoryMedianPriceAmount.                                                              |
| UAD1639 | Fatal    | PendingSales inventory requires MarketInventoryCount.                                                                                                         |
| UAD1642 | Fatal    | TotalSales inventory requires MarketInventoryCount.                                                                                                           |
| UAD1643 | Fatal    | TotalSales inventory with count greater than zero requires MarketInventoryHighestPriceAmount.                                                                 |
| UAD1645 | Fatal    | TotalSales inventory with count greater than zero requires MarketInventoryLowestPriceAmount.                                                                  |
| UAD1647 | Warning  | TotalSales inventory with count greater than zero requires MarketInventoryMedianPriceAmount.                                                                  |
| UAD1664 | Warning  | Carport or Garage requires CarStorageAreaMeasure.                                                                                                             |
| UAD1665 | Warning  | Carport or Garage requires CarStorageAttachmentType.                                                                                                          |
| UAD1669 | Warning  | Driveway or SharedDriveway requires ImprovedSurfaceMaterialType.                                                                                              |
| UAD1671 | Fatal    | Driveway or SharedDriveway with TenOrMoreParkingSpacesIndicator false, or any of the six independently applicable storage types, requires ParkingSpacesCount. |
| UAD1672 | Warning  | Driveway or SharedDriveway requires TenOrMoreParkingSpacesIndicator.                                                                                          |
| UAD1673 | Fatal    | CommonCarport, OpenLot, or ParkingGarage requires ProjectParkingSpaceAssignmentType.                                                                          |
| UAD1687 | Fatal    | Dwelling improvement requires DwellingExteriorDefectsExistIndicator.                                                                                          |

For UAD1671, the six independently applicable types are
Carport, CommonCarport, Garage, OpenLot, Other, and
ParkingGarage.

## What we will build

We will extend the existing fixture generator and test runner and retain standalone XML cases organized by source rule.

| Artifact | Project-relative location | Planned change |
|---|---|---|
| Fixture generator | `scripts/testing/generate_it_1_r1_s1_fixtures.py` | Add reproducible case definitions for the selected 30 rules while preserving prior cases. |
| Saved XML cases | `tests/fixtures/it_1/r1/s1/<RuleID>/<case-name>.xml` | Add independently inspectable, schema-valid test inputs. |
| RDF manifest | `tests/fixtures/it_1/r1/s1/manifest.ttl` | Record new case facts, provenance, hashes, and independently derived expected outcomes. |
| Behavioral tests | `tests/test_it_1_r1_s1_conditional_scoped_requirements.py` | Extend coverage and report each XML case separately through pytest parameterization. |
| Test summary | `docs/testing/IT-1R1-IT-1R1S1-slice-02-test-summary.md` | Record the plan, then actual execution evidence and remaining limitations. |

The test runner will read saved XML. It will not generate or repair fixtures during test execution.

The manifest’s declared coverage must match the selected 30 rules. Prior-slice cases remain identifiable and available for regression testing.

The exact number of XML files will follow the explicit case matrix. Thirty source rules does not mean thirty XML fixtures or thirty pytest cases.

## Required case coverage

### Three behavioral states for every rule

Each rule must have cases demonstrating:

1. Applicability unsatisfied and dependent data absent: no finding for the selected rule.
2. Applicability satisfied and dependent data absent: the expected finding.
3. Applicability satisfied and dependent data supplied: no finding for the selected rule.

A supplied value must be valid for the source field and XSD. False and zero must not be mistaken for absence where those values are allowed.

### Instance isolation for every rule

Each rule must also have cases with multiple schema-permitted instances that demonstrate:

- A compliant applicable instance cannot supply the dependent value for a different deficient applicable instance.
- An applicable compliant instance cannot cause a nonapplicable instance to be reported.
- Two deficient applicable instances produce two findings identifying their respective contexts.

Where a rule has multiple condition fields, add a case in which those fields are split across instances. They must not combine into a condition that is true in neither instance.

Use the relevant repeating ancestor when the detail container itself is not repeatable.

### Condition-specific cases

**Equality and value sets**

Exercise each listed applicable value and a schema-valid nonapplicable value. For UAD1147, cover all six room-type/update-status combinations and independently falsify each part of the conjunction.

**Presence conditions**

For UAD1100 and UAD1101, distinguish absent trigger data from present trigger data. Keep the reciprocal requirements independently observable by evaluating the selected rule.

**Inequality conditions**

For UAD1294, UAD1298, and UAD1330, exercise the explicitly excluded value and a valid value outside that exclusion. Do not interpret an absent trigger field as automatically satisfying an inequality.

Any expected behavior involving missing applicability inputs must be grounded in the source requirements before becoming a behavioral assertion.

**Numeric conditions**

For the seven market-inventory rules requiring a count greater than zero, cover zero and one, plus an applicable positive count in the wrong inventory type.

Use numeric comparison rather than string ordering. Do not introduce schema-invalid negative counts solely to test the boundary.

**OR conditions**

For UAD1556, activate the exterior and interior branches independently, covering Physical and Virtual for each. Also cover both branches active and neither active.

**Mixed conditions**

For UAD1671:

- Exercise Driveway and SharedDriveway with the indicator false.
- Exercise both with the indicator true.
- Exercise each of the six independently applicable types.
- Verify that the indicator restriction does not leak into the independent branch.
- Include a schema-valid nonapplicable type if the governed enumeration provides one.

Every applicable branch needs missing-dependent and supplied-dependent evidence.

## Fixture construction and validation

Use the established appraisal baseline and combined UAD XSD. Record their identities and hashes in the fixture provenance.

The generator must:

1. Build cases through explicit, reviewable changes to the baseline.
2. Preserve namespace correctness and schema element order.
3. Emit a portable relative `xsi:schemaLocation` that resolves from the saved fixture’s location.
4. Remove unused namespace declarations through the saved generator’s serialization process.
5. Validate the serialized XML against the combined XSD.
6. Check the case’s intended condition values, dependent-data state, and repeated-instance structure.
7. Compute the manifest hash from the final serialized bytes.
8. Validate the complete case collection and Turtle manifest before publishing generated outputs.

A fixture that fails XML parsing, schema validation, or its own declared case facts cannot establish RED.

Generation must remain reproducible from the saved project script. Manual corrections to generated XML must not become the only working version of a case.

Default generator execution remains non-writing. After saving and reviewing the generator, the user performs regeneration with:

`python scripts/testing/generate_it_1_r1_s1_fixtures.py --write --replace-generated`

Retain protection against overwriting fixture edits that do not match the existing manifest.

## Manifest and assertion design

Each case will identify:

- Stable case ID, scenario, slice, and source rule.
- Source row, source Unique ID, and Message ID as distinct identifiers.
- XML path, final hash, and baseline provenance.
- Purpose and deliberate fixture changes.
- Applicability and dependent-data states.
- Fixture checks establishing the intended input.
- Expected finding count, severity, violation kind, and affected XML contexts.

Expected outcomes must come from the source rule and explicit case design, independently of the production evaluator.

Tests will isolate the selected rule, verify governed source metadata, validate fixture integrity, invoke the existing validator interface, and compare actual findings with the manifest.

Each XML case will be independently reported. A failure in one case must not prevent later cases for that rule from running.

Assertions must check exact multiplicity and affected context, not merely the presence of a rule ID. Validation must leave the input unchanged.

## RED and GREEN boundaries

RED construction includes fixture generation, manifest entries, and test changes. It does not include production support for these 30 rules.

A valid RED result demonstrates missing or incorrect behavior on a valid fixture. Missing files, incorrect hashes, schema failures, collection errors, and unavailable dependencies are setup defects.

Some cases may already pass. In particular, a nonapplicable case can pass because a rule is not evaluated at all. Such a pass does not establish implementation.

After RED is explained and independently confirmed by the user, GREEN work begins only with explicit authorization.

GREEN requires:

- All new cases passing.
- Prior-slice cases remaining green.
- Correct Warning and Fatal severities.
- Correct instance isolation and finding multiplicity.
- Focused and complete-suite regression evidence.

Any complete-suite command that writes project reports must be identified before execution and follow the user-applied workflow.

## External endpoint reuse

Saved XML and provider-independent expected outcomes support later endpoint testing.

Schema validity is required, but it does not establish submission readiness or acceptance by an external service. Fixtures may contain unrelated compliance findings.

Future endpoint adapters must retain the selected-rule expectations while accounting explicitly for unrelated findings. No endpoint adapters or external submissions are part of this slice.

## Execution evidence

| Evidence | Status |
|---|---|
| Proposed membership contains 30 distinct rules | Confirmed in GraphDB by the user |
| Detailed case matrix and fixture count | Pending construction |
| Generator saved and reproducibility verified | Pending |
| All generated XML validated against XSD | Pending |
| Manifest parsing, coverage, facts, and hashes verified | Pending |
| User fixture review | Pending |
| Focused RED and failure analysis | Pending |
| User confirmation of RED | Pending |
| GREEN implementation and focused execution | Pending |
| Prior-slice and complete-suite regression | Pending |
| External endpoint execution | Outside this slice |

Record execution commands, environment, tested revision or working-tree state, source-rule count, XML-case count, pytest results, and retained evidence locations.

Do not mark the full Rule or Scenario complete when only this slice is finished.