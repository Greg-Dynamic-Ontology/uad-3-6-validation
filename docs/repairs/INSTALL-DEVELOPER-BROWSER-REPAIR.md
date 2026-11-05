# Restore the Developer browser checks while preserving Demo behavior

Extract `developer-browser-repair.zip` into `C:\Users\grego\projects\uad-3-6-validation`, replacing the matching files listed below.

## Replacement files

- `C:\Users\grego\projects\uad-3-6-validation\app\api\customer_validation_entry.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_rdf_projection_browser.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_rdf_projection_developer_experience.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_required_data_browser.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_schema_loader_developer_coverage.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_schema_loader_unrecognized_component.py`

## Behavior and test alignment

The application now offers `/validation/developer/` for the technical browser experience. It checks the active RDF experience profile and requires pipeline controls, technical artifacts, and developer diagnostics to be enabled. User configuration returns HTTP 403 for this entry. This is the existing presentation capability policy; it does not grant customer-account permissions, credits, or sign-in rights.

The default `/validation/` page retains Demo presentation, even when the configured experience is Developer. Customer upload, existing identity checks, account entry, cycles, and operating-mode selection retain their existing behavior.

The technical page reuses the actual validation HTML with a correct base URL, labels the presentation “Developer experience”, and loads the configured experience instead of the Demo presentation override. No browser JavaScript or static HTML replacement is needed.

Five older test modules now open the explicit Developer entry. The projection-selection test also explicitly sets and restores its Developer configuration instead of depending on inherited application state. Existing pipeline, artifact, source finding, severity, XML context, component-count, and processing-status assertions remain intact.

Two required-data display-label expectations are updated to the IT-46 report wording: “Business-rule findings” and “No business-rule findings were detected within the evaluated coverage.” The old 53-rule message is not restored.

A new IT-4R3S2 policy check confirms the default Demo page stays nontechnical, the Developer page exposes the controls under Developer configuration, and User configuration denies that entry.

## Focused regression

From `C:\Users\grego\projects\uad-3-6-validation`:

```bat
".venv\Scripts\python.exe" -B -m pytest tests\test_rdf_projection_browser.py tests\test_rdf_projection_developer_experience.py tests\test_required_data_browser.py tests\test_schema_loader_developer_coverage.py tests\test_schema_loader_unrecognized_component.py tests\test_rdf_projection_user_experience.py -q --tb=short -p no:cacheprovider
```

These tests start their own local server and isolate sign-in setup where required. No manually running server is needed for this focused command.

For manual use, restart the application after replacing the Python route file. With the Developer experience configured, open `http://localhost:4000/validation/developer/`. The usual customer/Demo entry remains `http://localhost:4000/validation/`.

## Verification

The repaired browser group, related schema checks, policy boundary, and unchanged User experience: **10 passed in 22.65s**.

Verification loads complete review modules against the installed application while preserving original project paths. The actual project files remain unchanged until you install the package. Full repository regression is a separate gate after the remaining failure groups are resolved.

Additional unchanged IT-46 browser integration checks: **8 passed, 54 deselected in 74.82s**, covering saved-run review, downloads, corrected resubmissions, fresh customer uploads, malformed XML, and evaluator outage/recovery. The 54 fixture-only cases were outside this focused compatibility check.
