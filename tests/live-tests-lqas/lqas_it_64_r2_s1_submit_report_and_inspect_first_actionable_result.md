# Live QA Script — IT-64R2S1

Scenario: **Submit a report and inspect its first actionable result through the browser.**

Status when authored: **NOT RUN through real hosted authentication.** A successful submission executes real validation, creates durable test records, and consumes one development validation credit.

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

## Controlled report and credit prerequisite

Use the matching pytest check for the exact controlled fixture. It copies the published report into a temporary file and removes AddressLineText only from the first subject PROPERTY/ADDRESS. It does not alter the published source:

`C:\Users\grego\projects\uad-3-6-validation\specs\fannie-mae\Appendix D-1 SF1_Appraisal\SF1_Appraisal_v1.4.xml`

Expected governed finding: **UAD1001**, source row **0100.0007**, at the subject-property address. Additional legitimate current-date findings can appear in this historical source; they must not conceal the expected finding.

For a separate entirely manual walkthrough, make a controlled copy under:

`C:\Users\grego\projects\uad-3-6-validation\test-files\fannie-mae\Appendix D-1 SF1_Appraisal\SF1_Appraisal_v1.4-less-subject-AddressLineText.xml`

Preserve the original, record both file digests, and remove only AddressLineText from the first PROPERTY with ValuationUseType="SubjectProperty", directly under its ADDRESS. Record the edit. This manual copy is not supplied or silently generated by this Markdown script. If unsure about the occurrence, use the test-generated controlled fixture instead.

The account must have at least one available development credit. The account page shows **Available validation credits**; **Validate Appraisal** must be enabled. To provision explicitly synthetic credits for the dedicated local test store, stop the server and run:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\add_development_test_credit.py" --apply --quantity 2
```

Only acknowledge **DEVELOPMENT TEST DATA** for the dedicated local test store. Restart the server afterward. This is test provisioning, not a purchase, and two credits are enough for this scenario and R2S2 once each.

## Manual browser walkthrough

1. Complete real sign-in and open the intended **Account report validation** page. Confirm the visible user and account against the profile.
2. Record the account's existing cycle IDs using **View recorded validation cycles**, then return to the account page.
3. Click **New validation cycle**. Expect a preparation section and **Appraisal XML report** file chooser. Merely opening the chooser must not create a cycle.
4. Choose the controlled missing-address report. Confirm the intended filename is selected.
5. Open the browser Network panel if collecting HTTP evidence. Click **Validate Appraisal** once.
6. Expect **Validating the report…** while the request executes. The browser must send **POST /validation-cycles?customer_account_id=...** and receive **HTTP 201 or 202**, identifying the new cycle and requested account. A schema-only or RDF-projection request does not satisfy this scenario.
7. Expect navigation to an account result page with a new cycle ID, heading **Open**, selected filename, and separate **Result, Submission, Attempt, and Run** identities.
8. Under **Findings**, locate **UAD1001**, its problem explanation, and **XML context** identifying the affected subject address. Confirm row **0100.0007** in the retrieved run JSON. The visible context must concern the actual edited occurrence.
9. Under **Coverage evaluated**, record the schema reference/version and selected constraint-set identity/version. Expand **Exact evaluated coverage**. A supported subset must not be presented as all published constraints.
10. Reload the result page. It must display the same saved cycle/result, not create another submission.
11. Inspect the detail and run endpoints in the same authenticated browser, replacing placeholders with recorded IDs:

   - `http://localhost:4000/validation-cycles/CYCLE_ID?customer_account_id=ACCOUNT_ID`
   - `http://localhost:4000/validation-runs/RUN_ID`

   Expect one accepted submission with its own ID, timezone-aware acceptance time, retained-artifact reference and digest; one linked attempt; an actionable nonpassing result; pending→open history; and one billable_validation_service_delivered lifecycle event. The independently retrieved run must match the result's nested validation_run.
12. Confirm the inventory has exactly one new cycle and the controlled upload and published original remain unchanged. Repeated genuine submissions consume additional credits and are not part of this single execution.

## Guided exact-fixture execution

Run the matching pytest command below to have the test prepare its own temporary controlled XML, drive the visible browser, compare the exact UAD1001 result with the real engine's independent output, and verify times, digests, identities, history, inventory, and source preservation. Complete real sign-in and let the test perform the upload; do not submit a second manual upload in its browser.

## Outcome

- **GREEN:** expected finding and context, correct account-owned open lifecycle, retained source/provenance, matching saved run and billable event, and passing exact-fixture acceptance test.
- **RED:** an apparent pass despite the defect, missing finding/context/identity, duplicate creation, wrong account, altered source, or dishonest coverage.
- **BLOCKED:** authentication/email, credits, prepared fixture/source, or server prerequisite is unavailable.

## Matching pytest confirmation

Keep the server running. In the other terminal run:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\run_it64_tests.py" "C:\Users\grego\projects\uad-3-6-validation\tests\test_it_64_r2_s1_submit_report_and_inspect_first_actionable_result.py" --maxfail=1
```

Complete real hosted sign-in inside pytest's visible browser. Allow pytest to finish and save its final summary and any failure diagnostic. Each standalone invocation may require sign-in again; shared real-session reuse lasts only within one pytest process.
