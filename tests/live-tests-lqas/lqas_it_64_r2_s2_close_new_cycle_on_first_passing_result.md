# Live QA Script — IT-64R2S2

Scenario: **Close a new cycle when the first actionable result passes.**

Status when authored: **NOT RUN through real hosted authentication.** This executes real validation, creates one durable test cycle, and consumes one development validation credit.

## Execution record

| Item | Record |
| --- | --- |
| Date, tester, application commit | |
| Expected UAD user ID and display name | |
| Expected customer account ID and label | |
| Browser | |
| Result | NOT RUN / GREEN / RED / BLOCKED |
| Evidence and diagnostic | |

Record identifiers and relevant status messages. Exclude passwords, API keys, usable cookies, verification codes, and callback query strings from evidence.

## Start here: identity, server, and email

- UAD application sign-in: **http://localhost:4000/login**, using **developer@dynamicontology.com** and that user's **UAD/AuthKit password** from the UAD Personas mSecure record.
- WorkOS dashboard sign-in: **https://dashboard.workos.com/**, using your administrator **greg.alvord@gmail.com** and the dashboard's existing sign-in method. Dashboard sign-in does not sign the test user into UAD.
- Email: developer@dynamicontology.com is now able to send and receive ordinary messages. Read its messages in the working Outlook inbox. The Namecheap mailbox password is separate from the UAD/AuthKit password.
- Expected local identity/account values are in `C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r1\s1\customer-profile.json`. It contains expectations, not credentials. Do not recreate the existing test account or replace its linked WorkOS `user_...` identity.

In the **server terminal**, start the application if needed:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\run_server.py"
```

Supply the Client ID and API key for the same UAD WorkOS environment. The registered callback for this run is exactly **http://localhost:4000/auth/callback**. Wait for **Application startup complete**. Leave that terminal running throughout QA. Run tests in a **different terminal**.

### Resolve the current verification-email blocker first

1. Open a fresh private browser window at **http://localhost:4000/login**. Use the existing developer user and choose **Sign in**, not **Sign up**.
2. At **Verify your email**, confirm the displayed recipient is **developer@dynamicontology.com**. Request one fresh verification message; note the request time.
3. Look for the fresh WorkOS email in the working inbox, Junk, and Spam folders. Enter the newest code in the same browser that requested it. An ordinary test message proves mailbox delivery only; it does not prove WorkOS delivery.
4. If the WorkOS message is absent, mark this execution **BLOCKED: WorkOS verification email not received**. In the WorkOS dashboard's **UAD-Development** environment, open **Users → developer@dynamicontology.com → Emails** and inspect the attempt at the recorded time. Record **Submitted / Delivered / Bounced / Failed**, or **no matching entry**. Hover over Bounced/Failed for the reason. Delivery history is available in sandbox environments; suppression management is not. If no attempt is recorded, inspect **Emails → Configuration** for the verification-email sending setting. [WorkOS email delivery documentation](https://workos.com/docs/email)
5. Save evidence of the delivery status/diagnostic and stop this script at BLOCKED until verification succeeds. Successful ordinary mail delivery alone is not a reason to change DNS, IMAP, or passwords again.

This manual diagnostic can take as long as needed. Pytest allows three minutes for interactive authentication. When using pytest, complete authentication inside **the browser pytest opened**. A session in a separate browser does not authenticate pytest.

## Passing report and coverage prerequisites

Use these installed controlled fixtures:

- Report: `C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r2\s2\sf1-controlled-current-dates.xml`
- Expected digest/coverage: `C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r2\s2\passing-case.json`
- Recorded source and date edits: `C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r2\s2\fixture-provenance.json`

The report is a separate SF1 copy with documented date shifts, not an edited published original. It was verified against the pinned governed schema and selected business coverage when prepared. Date-sensitive rules and source updates can invalidate that expectation later; an arbitrary published sample or empty XML is not a replacement positive control. Record RED or BLOCKED with the precise fixture/coverage diagnostic if its preconditions no longer hold; do not suppress findings or relabel the live result as passing.

Have at least one available development credit. The synthetic-credit preparation command is documented in **test_it_64_r2_s1_submit_report_and_inspect_first_actionable_result.md** in this same folder. Provisioning is explicit; tests do not silently replenish credits.

## Manual browser/API walkthrough

1. Complete real sign-in and open the intended account page. Verify user and account and record existing cycle IDs before submission.
2. Click **New validation cycle**, choose the controlled passing report above, and confirm **Validate Appraisal** is enabled.
3. Open the browser Network panel, then click **Validate Appraisal** once. This invokes the real API from the existing UI; verify **POST /validation-cycles** returns **201 or 202**. The exact direct-API request is also exercised by the matching pytest test below.
4. Expect a saved result page headed **Passed and closed**, identifying the selected filename and cycle, submission, attempt, result, and run IDs. A successful HTTP response alone does not establish a passing lifecycle result.
5. Expect no validation findings. Record the governed schema reference and selected constraint-set version under **Coverage evaluated**, and inspect **Exact evaluated coverage**. Compare identities and digests with passing-case.json.
6. In the same signed-in browser, open the saved cycle detail:

   `http://localhost:4000/validation-cycles/CYCLE_ID?customer_account_id=ACCOUNT_ID`

   Replace both placeholders with the recorded actual IDs. Confirm:

   | Saved evidence | Required value |
   | --- | --- |
   | cycle.state | passed-and-closed |
   | cycle.customer_account_id and actor_id | Expected account and verified local user |
   | submissions / attempts | Exactly one of each, with correct links |
   | submission integrity_digest | Matches passing-case.json report_sha256 |
   | accepted_at / started_at / completed_at | Timezone-aware and correctly ordered |
   | current_result.actionable / passed | true / true |
   | validation_run.findings | Empty |
   | validation_run.schema | Valid, governed schema digest/version matches the manifest |
   | validation_run.coverage | Complete for the explicitly selected coverage |
   | validation_run.summary | All severity counts zero |
   | history | pending directly to passed-and-closed; no open transition |
   | credit_lifecycle_events | Exactly one billable_validation_service_delivered event linking this result |

7. Retrieve **http://localhost:4000/validation-runs/RUN_ID**. Its JSON must match the nested validation_run in the saved cycle result.
8. Return to and reload the account result page. Expect the same **Passed and closed** result and provenance. Viewing must not run validation again or add history entries.
9. Check the account inventory gained exactly this one cycle. Confirm the controlled report digest is unchanged.

## Guided direct-API execution

Run the matching pytest command below for the exact direct-API submission and assertions. Complete real sign-in in the visible browser; the test submits the controlled XML, verifies the passing lifecycle and coverage, and opens the saved browser result automatically. Do not manually submit a second copy during that test.

## Outcome

- **GREEN:** actual API execution produces the correctly linked first actionable passing result, closes the pending cycle directly, preserves exact source/coverage, renders the saved passing result, and the matching test passes.
- **RED:** findings or incomplete execution are concealed as passing, an open transition occurs first, identity/digest/provenance differs, or a reload mutates the run.
- **BLOCKED:** sign-in/email, credit, reviewed fixture/coverage, or server prerequisite is unavailable.

## Matching pytest confirmation

Keep the server running. In the other terminal run:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\run_it64_tests.py" "C:\Users\grego\projects\uad-3-6-validation\tests\test_it_64_r2_s2_close_new_cycle_on_first_passing_result.py" --maxfail=1
```

Complete real hosted sign-in inside pytest's visible browser. Allow pytest to finish and save its final summary and any failure diagnostic. Each standalone invocation may require sign-in again; shared real-session reuse lasts only within one pytest process.
