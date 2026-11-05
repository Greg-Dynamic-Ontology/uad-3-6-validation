# IT-46R4S1 integrated customer upload repair

Replace these complete project files using the matching files in this package:

- `C:\Users\grego\projects\uad-3-6-validation\app\api\customer_validation_entry.py`
- `C:\Users\grego\projects\uad-3-6-validation\site\assets\js\validation.js`

The ZIP preserves their project-relative directories. Extract it into `C:\Users\grego\projects\uad-3-6-validation` to replace the files. No acceptance tests or XML fixtures need changes.

## Behavior

When the existing validation page is opened by a verified signed-in identity with the local account link required by POST `/validate/uad36`, the server marks the page as supporting integrated uploads. Fresh uploads then use that same endpoint for the real governed schema assessment and selected business rules. Results, failure guidance, coverage, and downloads use the existing IT-46 renderer. Corrected files continue through integrated validation as new runs.

The page marker controls presentation only. The POST endpoint still independently verifies identity and account linkage. The page response is private to the request (`Cache-Control: no-store`, `Vary: Cookie`). No cycle, account, validation attempt, credit debit, or new authorization is created merely by opening the page.

Anonymous Demo entry retains its existing behavior. Explicit technical pipeline choices retain their existing processing paths. This repair does not implement paid account-owned lifecycle submission, complete the unselected constraint backlog, or introduce durable run storage.

## Run IT-46R4S1

```bat
".venv\Scripts\python.exe" -B -m pytest tests\test_it_46_r4_s1_verify_integrated_customer_workflow.py -q --tb=short -p no:cacheprovider
```

## Run all current IT-46 acceptance tests

```bat
".venv\Scripts\python.exe" -B -m pytest tests -k "it_46_" -q --tb=short --durations=10 -p no:cacheprovider
```

The browser tests start their own local application server. For manual QA, restart your running application after copying the Python file and reload the browser assets.

Full repository regression remains a separate gate before the IT-46 commit. A pass of these scenario tests alone does not prove that gate.

## Existing checks outside IT-46

Two older technical-browser tests fail on hidden Demo-page controls. Both failures were independently reproduced without the repair:

- `C:\Users\grego\projects\uad-3-6-validation\tests\test_rdf_projection_browser.py`
- `C:\Users\grego\projects\uad-3-6-validation\tests\test_rdf_projection_developer_experience.py`

The unchanged baseline run of these two files reports **2 failed in 41.46s**. This repair does not edit their assertions or relax Demo policy to hide those existing failures. They remain items to resolve before claiming a clean full repository regression.

## Verification of this repair

- The three previously failing IT-46R4S1 browser cases passed: **3 passed, 54 deselected in 40.51s**.
- The complete IT-46 acceptance set passed: **71 passed**.
- Combined with three older projection browser checks, the result was **72 passed, 2 failed in 487.33s (8:07)**. The two failures are the independently reproduced baseline failures listed above.
- The unchanged anonymous Demo user-experience test passed.
- Review verification served the proposed JavaScript and loaded the proposed route module while preserving original project resource paths. No test responses were substituted. Actual project implementation files and acceptance tests were not edited.
- Full repository regression has not been run.
