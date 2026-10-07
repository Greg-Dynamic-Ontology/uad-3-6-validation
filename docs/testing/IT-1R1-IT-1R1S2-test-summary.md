# IT-1R1 / IT-1R1S2 test summary

## Status

**Partial GREEN: the `fixtureFamilyOutbuilding` slice is implemented and
its focused tests pass.** This completes 5 of the scenario's 27 selected
source rows. The dwelling structure, dwelling system, and manufactured
home families remain pending. The wider repeated-cross-and subgroup has
41 members; this scenario selects 27 of them.

The user confirmed RED for the corrected outbuilding corpus (**10 failed,
10 passed**) and authorized GREEN. The focused GREEN run passed **20 tests
in 2.39s**. Full regression and commit remain pending.

## Behavior

Iteration: IT-1

Rule: Other conditional or scoped requirements follow their governed
applicability.

Scenario: Require data in each instance when all correlated conditions
hold.

Authoritative feature:

features/spreadsheet-rule-category-validation.feature

For each selected source rule, evaluate the conditions correlated to
each governed XML instance.

When all conditions hold and required data is absent, report a finding
identifying that instance and the original source rule.

Conditions or supplied data belonging to another instance must not
activate or satisfy this instance's requirement.

## Selected source scope

The tracking TTL assigns 41 source rules to:

urn:uad36:work-tracking:r1-implementation-subgroup:repeated-cross-and

This is our implementation classification, not GSE terminology.

Original CSV rows govern rule logic, identity, severity, message, and
property scope. The classification is a starting point for binding
review; it does not itself establish executable applicability.

| Message ID | Required data |
| --- | --- |
| UAD1055 | HeatingSystemExistsIndicator |
| UAD1059 | UtilityTypeOtherDescription |
| UAD1060 | StructuralDesignType |
| UAD1064 | EstimatedRemainingEconomicLifeYearsCount |
| UAD1065 | ImprovementComponentType |
| UAD1077 | ImprovementComponentTypeAdditionalDescription |
| UAD1083 | StructureAreaMeasure |
| UAD1088 | FactoryBuiltCertificationExaminedIndicator |
| UAD1091 | StructureIdentifier |
| UAD1095 | StructureExcludingVehicleStorageAndADUFinishedAreaMeasure |
| UAD1096 | StructureExcludingVehicleStorageAndADUUnfinishedAreaMeasure |
| UAD1097 | NonContinuousFinishedAreaIndicator |
| UAD1098 | CoreHeatingSystemBelowGradeIndicator |
| UAD1107 | ManufacturedHomeInstalledDate |
| UAD1109 | ManufacturedHomeInvoiceReviewedIndicator |
| UAD1110 | ManufacturedHomeManufactureDate |
| UAD1114 | ManufacturedHomeMovedAfterOriginalInstallationIndicator |
| UAD1115 | ManufacturedHomePurchasedFromRetailerIndicator |
| UAD1116 | ManufacturedHomeRetailerInvoiceReviewedIndicator |
| UAD1117 | RoofLoadZoneCode |
| UAD1118 | SkirtingExistsIndicator |
| UAD1119 | ThermalZoneCode |
| UAD1120 | WindZoneCode |
| UAD1125 | ManufacturedHomeInstalledDateEstimatedIndicator |
| UAD1126 | ManufacturedHomeWidthType |
| UAD1158 | FloorIdentifier |
| UAD1193 | SaleType |
| UAD1240 | DataSourceName |
| UAD1241 | DataSourceQualityRatingCode |
| UAD1301 | ParcelAreaMeasure |
| UAD1333 | WaterAccessRightType |
| UAD1337 | WaterAccessDepthType |
| UAD1340 | WaterfrontDevelopmentRightsIndicator |
| UAD1382 | ExteriorConditionRatingCode |
| UAD1383 | ExteriorQualityRatingCode |
| UAD1491 | UnitTotalFinishedAreaMeasure |
| UAD1496 | RentControlStatusType |
| UAD1497 | UnitMonthlyActualRentAmount |
| UAD1498 | UnitMonthlyMarketRentAmount |
| UAD1588 | UPBProRataShareAttributableToUnitAmount |
| UAD1589 | UPBAmount |

All 41 were absent from the production loader in the coverage
reconciliation performed on 2026-10-05.

## Binding review

For every source row, identify:

- The repeated context owning the required value.
- Each applicability input and its XML container.
- The ancestor, property, or valuation analysis correlating those inputs.
- Whether an input is shared across instances or belongs to one instance.
- The allowed values, value sets, and numeric comparisons.
- The exact location expected in a finding.

Examples include conditions shared by a valuation report, conditions
belonging to an improvement, and conditions belonging to a particular
child record.

Shared report or property conditions must retain their governed scope.
Do not duplicate or relocate a shared condition merely to manufacture
an instance-local test.

Some source logic uses ConstructionMethod rather than
ConstructionMethodType. Preserve the source text and explicitly review
its XML binding. Do not silently rename source fields or invent an
interpretation.

Preserve unusual source formatting, including the line ending in
UAD1065's Unique ID cell. Record source metadata separately from derived
fixture bindings.

Any unresolved source meaning or binding must be reported explicitly.
It must not be converted into a guessed expectation or counted as RED.

## Artifacts to build

| Artifact | Project-relative path |
| --- | --- |
| Test summary | docs/testing/IT-1R1-IT-1R1S2-test-summary.md |
| Outbuilding fixture generator | scripts/testing/generate_it_1_r1_s2_outbuilding_fixtures.py |
| Standalone XML corpus | tests/fixtures/it_1/r1/s2/<MessageID>/<case-name>.xml |
| RDF manifest | tests/fixtures/it_1/r1/s2/manifest.ttl |
| Behavioral runner | tests/test_it_1_r1_s2_correlated_instance_requirements.py |

The existing IT-1R1S1 corpus and tests remain available for regression.

The new runner reads saved XML files and the Turtle manifest.
It does not generate XML fixtures inside the test code.

## Fixture construction

Derive fixtures from published UAD XML.

Prepare complete, consistent contexts for the selected requirement.
Create controlled variants by changing only documented applicability
inputs or the required dependent value.

Use multiple governed instances to test correlation and isolation.
Preserve schema ordering, unique labels, and valid relationships.

Validate every serialized fixture against the combined UAD schema
before writing it.

The generator must support:

- Default verification without writing files.
- Explicit corpus generation.
- Protected replacement of previously generated files.
- Reproducible XML and RDF generation.
- Source and fixture hash verification.
- Validation of the saved corpus.

The user runs the generator and reviews the generated files.

The final case and file counts will follow the reviewed binding matrix.
Forty-one source rules does not imply forty-one tests.

## Completed fixture family: Outbuilding

The tracker assigns five selected rows to `fixtureFamilyOutbuilding`:
UAD1055, UAD1059, UAD1083, UAD1095, and UAD1096. The generator creates
four two-Improvement cases for each row (20 XML fixtures total): two
applicable instances missing the target, one applicable instance missing
while its sibling supplies the target, both applicable instances supplied,
and condition inputs split across Improvement instances so no one
Improvement meets the full condition.

The split controls were reviewed against the XSD-bound source fields:
one Improvement is `Outbuilding` with its real-property indicator false;
the other is `Dwelling` with the indicator true. Thus neither individual
Improvement satisfies both conditions. UAD1055 also correlates
`LivingUnitCount` in `STRUCTURE_DETAIL` with the same Improvement's
`IMPROVEMENT_DETAIL`. UAD1059 evaluates `UtilityType` and its description
within each `OUTBUILDING_UTILITY`. The three area rules evaluate the
corresponding value in that Improvement's `STRUCTURE_DETAIL`.

Every serialized fixture validates against the combined UAD schema and
is recorded with its hash and expected per-instance findings in
`tests/fixtures/it_1/r1/s2/manifest.ttl`. The corrected split-case XML was
regenerated with protected replacement before the final RED and GREEN
runs.

## Required behavioral coverage

### Applicability

For each rule:

- All conditions hold; dependent data is absent: expected finding.
- All conditions hold; dependent data is supplied: no finding.
- Each condition is independently unsatisfied while the others hold:
  no finding.
- Exercise the governed alternatives within any value-set condition.
- Exercise numeric applicability boundaries where present.

Use only schema-valid condition and dependent values.

### Isolation between instances

Include applicable and nonapplicable instances together.

Verify:

- A finding identifies the applicable instance with missing data.
- No finding identifies a nonapplicable instance.
- Supplying the dependent value in another instance does not remove
  the finding.
- Supplying it in the affected instance removes the finding.
- Reversing the instance order preserves the correct affected context.
- Two applicable instances with missing data produce findings for
  both instances.

### Correlation across containers

Where condition inputs can be assigned independently, distribute them
across different owning contexts so that no context satisfies the full
conjunction. Expect no finding.

Do not combine a condition from one improvement, property, or valuation
analysis with a condition belonging to another.

For shared report or property conditions, test the shared condition
independently and keep its relationship to the repeated instances
explicit. Use separate owning contexts when needed to test isolation.

The case matrix must explain which inputs are shared and which are
instance-specific.

## Manifest evidence

manifest.ttl records:

- Iteration, Rule, Scenario, and subgroup.
- Exact selected source membership.
- Original Message ID and Unique ID cell.
- Original source logic, severity, message, scope, and XPath.
- Published source paths and hashes.
- Derived applicability and dependent-value bindings.
- Ownership and correlation contexts.
- Baseline preparation and controlled changes.
- Fixture paths and hashes.
- Expected findings and their affected locations.
- Schema validation evidence.
- Any reviewed source-binding or CSV/TTL differences.

Do not confuse source XPath values with derived fixture selectors.

## Test assertions

For each saved XML case:

1. Verify selected membership and original source identity.
2. Verify source metadata and declared hashes.
3. Validate the fixture against the combined UAD schema.
4. Independently verify its declared condition values and ownership.
5. Verify the declared presence or absence of the dependent value.
6. Evaluate the original CSV row through evaluate_required_data.
7. Assert the exact expected finding count.
8. Verify rule identity, severity, message, and source provenance.
9. Verify that each finding identifies the correct affected instance.
10. Verify that unrelated instances do not satisfy or activate the rule.
11. Verify that evaluation leaves XML inputs and saved files unchanged.

The independent oracle must not call production applicability logic.

Evaluate the selected source row in isolation so unrelated business
rules do not obscure the expected result.

## RED criteria

RED must fail because production does not enforce the selected
correlated requirement.

A valid RED failure is an absent expected finding, an incorrect finding
count, or incorrect instance attribution.

The following do not establish RED:

- Invalid XML.
- Collection or import errors.
- Missing files.
- Hash or source metadata mismatches.
- Incorrect test bindings.
- Unresolved source interpretation.

Nonapplicable and supplied-data controls may already pass.

Report the actual results after running the focused selection.
Wait for the user's RED confirmation and GREEN authorization.

## Implementation boundary

During RED, construct only documentation, fixtures, manifest,
generator, and test runner.

Use the existing production evaluation interface.
Do not implement applicability behavior during RED.

Production validation must not depend on this test corpus or manifest.

This scenario establishes evaluator behavior. XML API submission of the
corpus remains separate endpoint coverage.

## Execution evidence

Source scope inspected: 41 subgroup members; 27 rules selected by
IT-1R1S2; 5 rules completed in the outbuilding family.

Outbuilding CSV and XSD binding review: Complete for UAD1055, UAD1059,
UAD1083, UAD1095, and UAD1096.

Fixture construction and schema validation: Complete; 20 XML fixtures
validate against the combined schema.

Saved corpus verification: Complete; manifest and XML hashes verified by
the focused runner.

Focused RED on the corrected corpus: 10 failed, 10 passed.

User RED confirmation: Confirmed.

GREEN authorization: Confirmed.

Focused GREEN: 20 passed in 2.39s.

Other fixture families and the remaining 22 selected source rows:
Pending.

Full regression: Pending.

Commit and push: Pending.