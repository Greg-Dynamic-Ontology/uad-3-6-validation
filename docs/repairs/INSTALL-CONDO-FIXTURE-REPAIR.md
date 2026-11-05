# Repair the 44 missing Condo XML fixture references

Extract `condo-fixture-reference-repair.zip` into `C:\Users\grego\projects\uad-3-6-validation`, replacing the matching files listed below. The ZIP preserves the project-relative directories.

The existing managed fixture is used directly:

`C:\Users\grego\projects\uad-3-6-validation\test-files\fannie-mae\Appendix D-1 Condo1_Appraisal\Condo1_Appraisal_v1.4-less-InspectorFileIdentifier-value.xml`

No XML file is copied, modified, renamed, or added. No changes are made to published source samples, evaluator logic, rule expectations, or assertion checks.

## Replacement files

- `C:\Users\grego\projects\uad-3-6-validation\data\uad36-test-suite\tests\fixtures\single_equality\test-suite.ttl`
- `C:\Users\grego\projects\uad-3-6-validation\data\uad36-test-suite\tests\fixtures\required_structures\required-structures-test-suite.ttl`
- `C:\Users\grego\projects\uad-3-6-validation\data\uad36-test-suite\tests\fixtures\uniqueness_cardinality\test-suite.ttl`
- `C:\Users\grego\projects\uad-3-6-validation\data\uad36-test-suite\tests\fixtures\numeric_bounds\test-suite.ttl`
- `C:\Users\grego\projects\uad-3-6-validation\data\uad36-test-suite\tests\fixtures\relationship_reference_integrity\test-suite.ttl`
- `C:\Users\grego\projects\uad-3-6-validation\utilities\generate_uniqueness_cardinality_test_suite.py`
- `C:\Users\grego\projects\uad-3-6-validation\utilities\generate_numeric_bounds_test_suite.py`
- `C:\Users\grego\projects\uad-3-6-validation\utilities\generate_relationship_reference_test_suite.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_validation_api.py`

## What changed

- Twenty-one stale baselinePath literals in five Turtle inventories now identify the existing managed fixture. A graph comparison verifies every other RDF triple is unchanged.
- Three generator source files use the same corrected path so regeneration does not restore the stale references. The generators were syntax-checked, not run against canonical artifacts.
- The schema-upload API test changes only its XML file location; its requests and assertions remain unchanged.

## Focused regression

From `C:\Users\grego\projects\uad-3-6-validation`, run this CMD command:

```bat
".venv\Scripts\python.exe" -B -m pytest tests\test_it_1_r2_single_equality_behavior.py tests\test_it_1_r3_s1_required_structure.py tests\test_it_1_r5_s1_uniqueness_cardinality.py tests\test_it_1_r6_s1_numeric_bounds.py tests\test_it_1_r9_s1_relationship_reference_integrity.py tests\test_validation_api.py -q --tb=short -p no:cacheprovider
```

## Verification

**701 passed in 53.02s**, covering all six affected modules and every original missing-fixture failure. The managed XML independently passes the governed GSE UAD XSD. A review overlay loaded the proposed inventories and the path-only API-test function while leaving the project checkout unchanged.

The original project files and the managed fixture digest were checked again before packaging. No new XML fixtures or acceptance tests were created. Other failure groups from the full regression are outside this repair; full repository regression was not repeated.

Managed fixture SHA-256: `dcc777bdd6f05c4425d2efbd70237cf6e989127d53b376ee9a105ef4d555396a`.
