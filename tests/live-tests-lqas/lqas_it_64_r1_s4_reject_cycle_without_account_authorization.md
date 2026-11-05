# Live QA Script — IT-64R1S4

Scenario: **Reject a cycle request without account authorization.**

Status when authored: **NOT RUN through real hosted authentication.** This is a guided live browser/API check with pytest providing the protected-store comparison.

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

## Prerequisites specific to this scenario

The existing developer user is a permitted validator in the normal dedicated test account. The unauthorized target must be a different account in which that same user lacks validation permission. An unsigned request or HTTP 404/405 is not proof of this rule.

The matching pytest test creates a temporary **owner-only** account membership for the real signed-in local user, without changing the user's existing roles. It records all protected SQLite tables before the denied requests, compares them afterward, and removes its unchanged temporary fixture. If an unexpected mutation occurs, it preserves the fixture for investigation. Use the same otherwise-idle dedicated store as the running server:

`C:\Users\grego\projects\uad-3-6-validation\data\customer-validation.sqlite3`

If UAD_CUSTOMER_STORE is configured, the server and tests must use that same configured path. Do not modify the production account or manually remove real permissions to prepare this check.

## Operator actions and evidence

1. Run the matching pytest command below in the test terminal.
2. In its visible browser, sign in as **developer@dynamicontology.com** and enter the new verification code. The real authenticated user's local ID must match the profile; anonymous rejection does not pass.
3. Let the test submit these three real API requests against its temporary owner-only account:

| Variant | What is attempted | Required result |
| --- | --- | --- |
| ordinary-request | Normal new-cycle request without target-account validation permission | HTTP 403 |
| claimed-validator | Body/header claim the verified user is a validator | HTTP 403 |
| conflicting-account-selection | Query requests the forbidden account while body/header name the authorized account | HTTP 403 |

4. Look for one terminal line per variant ending **HTTP 403; protected customer-store state unchanged.** The denial must explain permission, authorized access, membership, or validation access.
5. Confirm no cycle, submission, validation attempt, result, or credit debit was returned or recorded by these denied requests. Pytest's database comparison supplies this evidence; the absence of a UI result alone does not.
6. Let the test finish. It must report **1 passed**. If it reports **Fixture preserved for investigation**, retain the diagnostic and record RED rather than deleting the unexpected state.

## Outcome

- **GREEN:** a genuinely signed-in user is denied in all three variants, with unchanged protected storage and a passing matching test.
- **RED:** any forbidden request succeeds, trusts client identity/permission claims, changes protected storage, or fails to provide an authorization denial.
- **BLOCKED:** real sign-in, source report, prepared local account, shared store, or server is unavailable.

This scenario deliberately supplies database evidence through the acceptance test. It is not represented as a browser-only manual proof.

## Matching pytest confirmation

Keep the server running. In the other terminal run:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\run_it64_tests.py" "C:\Users\grego\projects\uad-3-6-validation\tests\test_it_64_r1_s4_reject_cycle_without_account_authorization.py" --maxfail=1
```

Complete real hosted sign-in inside pytest's visible browser. Allow pytest to finish and save its final summary and any failure diagnostic. Each standalone invocation may require sign-in again; shared real-session reuse lasts only within one pytest process.
