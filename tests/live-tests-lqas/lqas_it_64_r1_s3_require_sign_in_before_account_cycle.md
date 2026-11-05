# Live QA Script — IT-64R1S3

## Scenario

**Require sign-in before creating an account-owned cycle.**

An unauthenticated visitor requesting account validation must receive an actionable sign-in flow. The request must not create a customer-owned cycle or report submission, or disclose customer validation history.

## Test record

| Item | Record |
| --- | --- |
| Execution date and tester | |
| Application commit or version | |
| Browser and version | |
| Application address | `http://localhost:4000` |
| Dedicated customer account ID used | |
| Result | Not run / GREEN / RED / BLOCKED |
| Evidence and observations | |

Use a dedicated test account. Keep passwords, API keys, session-cookie values, and authentication codes out of the test record and screenshots.

## Before starting

1. Confirm the IT-64R1S3 router change is saved in:

   `C:\Users\grego\projects\uad-3-6-validation\app\api\customer_validation_entry.py`

2. If Python code changed since the server started, stop the old server with **Ctrl+C**. In Windows Command Prompt, start it again:

   ```bat
   cd /d C:\Users\grego\projects\uad-3-6-validation
   ".venv\Scripts\python.exe" -B utilities\customer-validation\run_server.py
   ```

3. Supply the WorkOS test Client ID, registered callback `http://localhost:4000/auth/callback`, and test API key when prompted. Leave this terminal running.

4. **Expected clue:** the terminal says application startup is complete and Uvicorn is running on port 4000. The launcher does not automatically reload Python changes.

5. Use `localhost` consistently in the browser. Open the running application through HTTP; do not open `site\index.html` from disk.

6. Have the actual dedicated customer account ID available from IT-64R1S1. In the addresses below, replace `ACCOUNT_ID` with that ID. An invented ID can check the sign-in prompt but cannot demonstrate protection of an existing account's history.

## A. Record the existing account's cycle inventory

1. In an ordinary browser window, sign in using the existing dedicated WorkOS test user:

   `http://localhost:4000/login`

2. Open:

   `http://localhost:4000/validation/?customer_account_id=ACCOUNT_ID`

3. **Expected clues:** the account page identifies the verified user and the selected customer account.

4. Select **View recorded validation cycles**, or open:

   `http://localhost:4000/validation-cycles?customer_account_id=ACCOUNT_ID`

5. Record the complete set of cycle identifiers and states as the **before** inventory. An empty `cycles` list is acceptable. Leave this signed-in window separate from the anonymous tests below.

**Stop as BLOCKED** if the dedicated account cannot be accessed. Do not label a missing account prerequisite as a failure of this scenario.

## B. Request account validation without signing in

1. Open a new private or Incognito browser session. Close any earlier private windows first so their shared private session is discarded.

2. Do not sign in in that private session. Enter:

   `http://localhost:4000/validation/?customer_account_id=ACCOUNT_ID`

3. Verify these visual clues:

   - Page heading: **Sign in for account validation**.
   - Explanation: **Sign in to request a validation cycle for your customer account.**
   - Notice: **No validation cycle or report submission has been created.**
   - An actionable **Sign in** link and a **Home** link.
   - No authenticated user name, customer-account details, report upload control, **New validation cycle** action, findings, or validation history.

4. **GREEN clue:** this is a usable HTML page, not a bare JSON response such as `{"detail":"Sign in to use customer-account validation."}`.

5. Capture the prompt as evidence, excluding sensitive browser information. The HTML response may legitimately have HTTP status **401**; the actionable sign-in page is what this browser check requires.

## C. Confirm that history is protected

1. In the same unsigned-in private session, open:

   `http://localhost:4000/validation-cycles?customer_account_id=ACCOUNT_ID`

2. **Expected clues:** an access-denied JSON diagnostic is shown, with no cycle list, submissions, results, or findings. For the present implementation, the diagnostic is **Sign in to use customer-account validation.**

3. If inspecting the Network panel, the expected API status is **401** or **403**. API denial can be JSON; the account-entry browser page in section B must provide the usable sign-in action.

4. **RED:** any customer validation history is disclosed without authentication.

## D. Follow the existing sign-in flow

1. Return to:

   `http://localhost:4000/validation/?customer_account_id=ACCOUNT_ID`

2. Select **Sign in**.

3. **Expected clues:** the browser follows UAD's `/login` route and reaches the real hosted WorkOS authentication page over HTTPS. It offers the configured sign-in options.

4. Stop before entering credentials. This part proves that unauthenticated account entry leads to authentication; completing sign-in is covered by IT-64R1S1.

5. **RED:** a dead link, JSON error in place of the sign-in flow, redirect loop, or access to the account page without authentication.

6. **BLOCKED:** WorkOS reports an invalid Redirect URI, missing configuration, or an external service/network failure. Record the diagnostic; these conditions do not demonstrate successful sign-in gating.

## E. Repeat with an invalid session

This checks an existing but unusable session cookie rather than only a browser with no cookie. Use the private test session, never a real customer's browser profile.

1. In that private session, open `http://localhost:4000/health`.
2. Open the browser's developer tools and its cookie editor for `http://localhost:4000` (in Chrome, **Application → Storage → Cookies**).
3. Add a cookie named `wos_session` with value `deliberately-invalid-it64r1s3-session` and path `/`. If a cookie of that name already exists in this private session, replace its value with this test value. Do not copy an actual session cookie into the test record.
4. Open the account-validation address from section B again.
5. **Expected clues:** the same **Sign in for account validation** page is displayed. No customer details, history, or creation action appears.
6. Repeat sections C and D. History must remain denied, and **Sign in** must still reach WorkOS.
7. The application may delete the invalid cookie while displaying the challenge; that is expected.
8. Close the private session after this test.

If the browser cannot create the test cookie, record this manual section as BLOCKED and use the automated invalid-session case below as separate evidence. Do not record the manual section as passed without exercising it.

## F. Verify unchanged records and run the automated companion

1. Return to the ordinary, signed-in browser window from section A. Refresh the account's cycle inventory.
2. Compare all identifiers and states with the before inventory.
3. **Expected clue:** the cycle inventory is unchanged. No new customer-owned cycle appears because of the anonymous entry, denial, or sign-in challenge.
4. Visual inspection alone does not prove the absence of hidden submissions or other storage mutations. Run the automated companion in a second terminal while the server remains running:

   ```bat
   cd /d C:\Users\grego\projects\uad-3-6-validation
   ".venv\Scripts\python.exe" -B -m pytest tests\test_it_64_r1_s3_require_sign_in_before_account_cycle.py --headed -q --tb=short -p no:cacheprovider
   ```

5. For an existing-account check, set the completed IT-64 profile in this test terminal before running pytest:

   ```bat
   set "UAD_IT64_CUSTOMER_PROFILE=C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r1\s1\customer-profile.json"
   ```

6. If using a custom `UAD_CUSTOMER_STORE`, the server and test terminal must point to the same store. Use an otherwise idle dedicated local test application so unrelated activity does not change the inventory during the check.
7. **Expected clue:** **2 passed**, covering absent and invalid sessions. No manual authentication is required for these two tests.
8. The companion compares protected records in the configured customer SQLite store before and after each request. An absent store must remain absent. Security audit entries may be added for denied access. The check does not inspect unrelated external stores.

## Completion criteria

Record **GREEN** when:

- Both missing-session and invalid-session browser entry require the existing sign-in flow.
- Neither entry exposes account controls or customer validation history.
- The account's cycle inventory remains unchanged.
- The automated companion passes both cases and confirms unchanged protected customer-store records.

Attach or reference the prompt screenshot, hosted sign-in screenshot, before/after inventory, and pytest summary. Record any manual section that was blocked separately.

This script verifies IT-64R1S3. It does not certify report submission, payment collection, or the full IT-64 workflow.
