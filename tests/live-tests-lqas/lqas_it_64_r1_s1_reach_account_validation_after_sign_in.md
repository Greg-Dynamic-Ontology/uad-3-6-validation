# Live QA Script — IT-64R1S1

Scenario: **Reach the account validation page after successful sign-in.**

Status when authored: **NOT RUN; real WorkOS email verification is the current
blocker.
** This script documents expected behavior and does not certify completion.

## Execution record

| Item                                   | Record                          |
|----------------------------------------|---------------------------------|
| Date, tester, application commit       |                                 |
| Expected UAD user ID and display name  |                                 |
| Expected customer account ID and label |                                 |
| Browser                                |                                 |
| Result                                 | NOT RUN / GREEN / RED / BLOCKED |
| Evidence and diagnostic                |                                 |

Record identifiers and relevant status messages. Exclude passwords, API keys, usable cookies, verification codes, and callback query strings from evidence.

## Start here: identity, server, and email

- UAD application sign-in: **http://localhost:4000/login**, using
**developer@dynamicontology.com** and that user's **UAD/AuthKit password** from
the UAD Personas mSecure record.
- WorkOS dashboard sign-in: **https://dashboard.workos.com/**, using your
administrator **greg.alvord@gmail.com** and the dashboard's existing sign-in method. Dashboard sign-in does not sign the test user into UAD.
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

## Manual steps and visual clues

1. Read the expected display name, UAD user ID, account ID/label, operating mode, and hosted sign-in hostname from `C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r1\s1\customer-profile.json`. Record them before the run.
2. Establish the account's cycle inventory before signing in. For a rigorous side-effect check, use the matching pytest confirmation below: it independently reads the shared SQLite store before authentication and compares the API inventory afterward. A browser screenshot alone cannot establish that no database records were created. Old `preexisting_cycle_ids` in the profile may predate legitimate later cycle tests; do not erase those cycles to force an empty inventory.
3. Start a fresh private browser session at **http://localhost:4000/**. Find and click a visible **Sign in** action. If the Demo disclosure appears, its Sign in link must be accessible. Going straight to /login is useful for diagnosing email, but does not prove this landing-page entry works.
4. Confirm the browser reaches the profile's real hosted sign-in hostname. Sign in as **developer@dynamicontology.com** and complete email verification. Do not register a replacement user.
5. Confirm the browser returns to UAD through **/auth/callback**, then identifies the verified user. A callback error, an endless verification screen, or an unlinked-user message does not pass.
6. Open the displayed customer-account validation link. Its URL is **http://localhost:4000/validation/?customer_account_id=ACCOUNT_ID**, with the actual expected account ID.
7. Compare these visible clues with the profile:

| Visual clue | Expected |
| --- | --- |
| Heading | Account report validation |
| Signed in as | Expected local display name |
| Customer account | Expected account label |
| Operating mode | Expected Standard or Developer mode |
| Demo indicator on this account page | Absent |
| New validation cycle | Visible and enabled |

8. **Do not click New validation cycle or submit a report during this scenario.** Viewing and sign-in must leave the independently recorded cycle inventory unchanged.
9. Run the matching pytest confirmation to verify exact identity/account attributes, the real hosted callback, and no cycle/submission-creation request or cycle-inventory change.

## Outcome

- **GREEN:** all browser clues match and the matching pytest test passes its no-side-effect checks.
- **RED:** verified sign-in completes but user/account/mode/action or no-side-effect checks fail.
- **BLOCKED:** missing server, verification email, callback configuration, or prepared identity/account prerequisite. Record the actual blocker instead of calling the product GREEN.

## Matching pytest confirmation

Keep the server running. In the other terminal run:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\run_it64_tests.py" "C:\Users\grego\projects\uad-3-6-validation\tests\test_it_64_r1_s1_reach_account_validation_after_sign_in.py" --maxfail=1
```

Complete real hosted sign-in inside pytest's visible browser. Allow pytest to finish and save its final summary and any failure diagnostic. Each standalone invocation may require sign-in again; shared real-session reuse lasts only within one pytest process.
