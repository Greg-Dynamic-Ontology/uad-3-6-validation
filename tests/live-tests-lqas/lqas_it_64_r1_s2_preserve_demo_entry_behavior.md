# Live QA Script — IT-64R1S2

## Scenario

**Preserve Demo entry behavior for a Demo visitor.**

Verify the IT-25R1 disclosure, cancellation, continuation, and visible Demo indicators in a real browser. Demo use must not authenticate the visitor, create customer-owned cycles, or consume account credits.

## Test record

| Item | Record |
| --- | --- |
| Execution date and tester | |
| Application commit or version | |
| Browser and version | |
| Application address | `http://localhost:4000` |
| Appraisal fixture | `SF1_Appraisal_v1.4.xml` |
| Customer store | Default / record configured override |
| Result | Not run / GREEN / RED / BLOCKED |
| Evidence and observations | |

Keep credentials, authentication codes, and session-cookie values out of test evidence.

## Before starting

1. Confirm that the server is running. If Python code changed, stop the previous server with **Ctrl+C** and restart:

   ```bat
   cd /d C:\Users\grego\projects\uad-3-6-validation
   ".venv\Scripts\python.exe" -B utilities\customer-validation\run_server.py
   ```

2. Supply the requested WorkOS test settings and registered callback `http://localhost:4000/auth/callback`. Leave the server terminal running. **Expected clue:** application startup completes and Uvicorn is running on port 4000.
3. Have the published test report available:

   `C:\Users\grego\projects\uad-3-6-validation\specs\fannie-mae\Appendix D-1 SF1_Appraisal\SF1_Appraisal_v1.4.xml`

4. Use a fresh private or Incognito browser session. Close older private windows first. Do not sign in or reuse the authenticated IT-64R1S1 browser session.
5. No customer-account provisioning or preexisting customer database is required for this anonymous scenario. If a customer store does exist, it must remain unchanged by the Demo test.
6. Open HTTP addresses, not local HTML files. Use an otherwise idle dedicated test server for the companion's storage comparisons.

## A. Inspect initial Demo entry

1. Open [the UAD landing page](http://localhost:4000/).
2. **Expected clues:**

   - A prominent **Demo Mode** indicator is visible.
   - A disclosure titled **Continue in Demo Mode?** is open before Demo validation can begin.
   - It explains that Demo provides no customer-owned validation cycles, account validation history, corrected submissions within an existing cycle, or purchasing/holding/consuming account credits.
   - Both **Cancel** and **Continue in Demo Mode** are visible and usable.
   - **Run Validation** is the primary landing-page action; **Documentation** is available as a secondary action.

3. Capture the disclosure and Demo indicator as evidence.
4. **RED:** missing disclosure, missing limitation text, an invisible Demo indicator, or validation starting before the visitor chooses to continue.

## B. Cancel entry

1. Select **Cancel**.
2. **Expected clues:** the dialog closes, the browser stays on the landing page, and the Demo indicator remains visible.
3. No file picker, upload, validation execution, or customer-cycle creation should occur because of cancellation.
4. Select **Run Validation**.
5. **Expected clue:** the disclosure opens again. Cancellation must not silently grant consent to enter Demo validation.

## C. Continue into Demo validation

1. Select **Continue in Demo Mode**.
2. **Expected clues:**

   | Page element | Expected |
   | --- | --- |
   | Browser location | `http://localhost:4000/validation/` |
   | Demo indicator | Visible **Demo Mode** |
   | Task | **Validate Appraisal** |
   | File selection | Available for an appraisal XML file |
   | Validation action | Enabled **Validate Appraisal** button |
   | Developer pipeline controls | Hidden |
   | Authenticated identity/account | No signed-in user or selected customer-account panel |

3. Continuing alone must not upload or validate a report. Do not mistake navigation into the page for a completed validation.
4. **RED:** the Developer server configuration reveals technical pipeline choices in this Demo workflow or removes the Demo indicator.

## D. Execute a Demo request

1. Use the file chooser to select:

   `C:\Users\grego\projects\uad-3-6-validation\specs\fannie-mae\Appendix D-1 SF1_Appraisal\SF1_Appraisal_v1.4.xml`

2. Select **Validate Appraisal** once.
3. **Expected clues:** processing begins and then a result is displayed, identifying `SF1_Appraisal_v1.4.xml`. The Demo indicator stays visible, and the validation button is enabled again when processing finishes.
4. This scenario checks that the existing Demo service works. Do not interpret a Demo projection or schema result as proof that every governed UAD constraint was evaluated.
5. **RED:** a request error replaces the service result, the workflow unexpectedly signs the visitor in, a customer cycle is created, or the UI leaves Demo mode.

## E. Confirm the visitor remains anonymous

1. In the same private session, open:

   `http://localhost:4000/account/context`

2. **Expected clue:** an authentication-required diagnostic appears instead of user or account details. The present response is HTTP **401** with **Sign in to use customer-account validation.**
3. Demo continuation and validation must not establish a `wos_session` authentication cookie. If using the browser's cookie inspector, check only the cookie's presence; do not record cookie values.
4. Close the private session when finished.

## F. Verify storage behavior with the automated companion

Visual checks alone cannot prove that no hidden credit debit or database write occurred. Keep the server running and use a second Command Prompt:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
".venv\Scripts\python.exe" -B -m pytest tests\test_it_64_r1_s2_preserve_demo_entry_behavior.py --headed -q --tb=short -p no:cacheprovider
```

1. No manual sign-in is required. The test opens its own fresh anonymous browser.
2. **Expected clue:** **1 passed** for Chromium.
3. The companion checks cancellation and continuation, actual Demo execution, persistent Demo indicators, denied account context, absence of authentication cookies, and absence of account-scoped or account-mutating requests.
4. It compares every table in the configured customer SQLite store before and after Demo use, including credit tables present there. If the store was absent, it must remain absent. It does not inspect unrelated external stores.
5. The default store path is:

   `C:\Users\grego\projects\uad-3-6-validation\data\customer-validation.sqlite3`

6. If using `UAD_CUSTOMER_STORE`, use the same value in the server and test terminals. Do not initialize a customer database merely to satisfy this Demo test.
7. If the published fixture has intentionally moved, set `UAD_IT64_DEMO_REPORT` in the test terminal to the actual full fixture filename and record the substitution. Do not edit the published report to obtain a pass.

## Completion criteria

Record GREEN when the initial disclosure is complete, Cancel stays on the landing page, Run Validation asks for consent again, Continue opens the anonymous Demo page, Demo validation produces its actual result, and the Demo indicator remains visible throughout. The visitor must remain unauthenticated and the automated companion must confirm unchanged customer storage and no account-side effects.

Reference screenshots of the disclosure, post-cancellation landing page, Demo result, and pytest summary. Record unavailable server/fixture prerequisites as BLOCKED and behavior mismatches as RED.

This script covers the preserved Demo workflow, not paid account validation or full UAD compliance coverage.
