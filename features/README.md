# UAD IT-64R1S1 Walkthrough
## Create a WorkOS user and sign in to UAD

This walkthrough prepares a real WorkOS test user for IT-64R1S1 and signs that
user into the local UAD application.

There are two records to establish:

- **WorkOS user:** the identity that authenticates through hosted AuthKit.
- **UAD user and customer membership:** the local records that determine which 
customer account the authenticated person can access and whether they can
validate reports.

Creating a WorkOS user does not automatically create the UAD customer account.
The local setup utility below supplies that test precondition.

## 1. Install the proposed IT-64 entry implementation

Before following these instructions, copy the proposed IT-64R1S1 implementation
files into their matching project destinations and save them.
In particular, these new utilities must exist:

- `C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\run_server.py`
- `C:\Users\grego\projects\uad-3-6-validation\utilities\customer-validation\prepare_test_account.py`

The proposed changes to `C:\Users\grego\projects\uad-3-6-validation\app\main.py`, the new account-entry router and store, and the website files must also be installed. The commands below depend on those changes.

## 2. Configure the WorkOS test application

Open the [WorkOS dashboard](https://dashboard.workos.com/) and select the test environment and application used by UAD. Keep the user, Client ID, and API key in that same environment.

Configure these application URLs:

| Setting            | Local UAD value                       | Purpose                                                                               |
|--------------------|---------------------------------------|---------------------------------------------------------------------------------------|
| Redirect URI       | `http://localhost:4000/auth/callback` | Receives the authentication response.                                                 |
| Initiate login URI | `http://localhost:4000/login`         | Starts the hosted authentication flow.                                                |
| Sign-out URI       | `http://localhost:4000/`              | Public destination after logout; configuring this does not implement a logout action. |

Preserve any other registered URLs that are still needed. Confirm the saved values.
The callback supplied by UAD must match an allowed Redirect URI exactly.
See the [AuthKit Python setup guide](https://workos.com/docs/authkit/vanilla/python)
and [session documentation](https://workos.com/docs/authkit/sessions).

For this walkthrough, use `localhost` consistently.
Do not alternate between `localhost` and `127.0.0.1` during sign-in.

Have the test environment's Client ID and API key available.
Do not paste the API key into this README or commit it to Git.

## 3. Start the UAD server

Open a Windows Command Prompt. Stop any older UAD server already using port 4000,
then run:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
".venv\Scripts\python.exe" -B utilities\customer-validation\run_server.py
```

Supply the requested values:

1. WorkOS test Client ID.
2. Registered Redirect URI: `http://localhost:4000/auth/callback`.
3. WorkOS test API key. Its input is hidden.

The launcher passes the settings to the server process.
They do not become variables in the parent Command Prompt.
It supplies a session-cookie password automatically when one is not already
configured.

Leave this terminal running.
Confirm that Uvicorn reports port 4000 is ready.

## 4. Create the WorkOS user

Open [UAD sign-in](http://localhost:4000/login) in your browser.
This starts authentication through UAD and sends you to the application's hosted
AuthKit page.

On that hosted page:

1. Record the **hostname** from the browser address bar.
The local test setup will ask for it later.
Copy only the hostname, without `https://`, a path, or query parameters.
2. Choose the sign-up option if this is a new test user.
3. Use an email address whose inbox you can access, and complete the enabled
registration and verification steps.
4. If the test user already exists, sign in with that user's existing
authentication method instead.

AuthKit provides sign-up, sign-in, password-reset, and email-verification flows.
The available methods depend on the WorkOS environment's configuration.
See [hosted AuthKit](https://workos.com/docs/authkit/hosted-ui) and
[email and password authentication](https://workos.com/docs/authkit/email-password).

After authentication, WorkOS returns the browser to UAD through
`/auth/callback`.
At this point UAD may report that the authenticated identity has no local
account linkage. Continue with the next step.

In the same WorkOS test environment, open the new user's record and copy its
**WorkOS user ID**.
This is different from the email address and the application Client ID.

## 5. Link the identity to a UAD test account

Open a second Command Prompt while the server remains running:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
".venv\Scripts\python.exe" -B utilities\customer-validation\prepare_test_account.py
```

Answer the prompts:

| Prompt                                 | What to enter                                                                |
|----------------------------------------|------------------------------------------------------------------------------|
| Existing WorkOS user ID                | The actual user ID copied from WorkOS.                                       |
| Test user display name                 | The name to display in UAD.                                                  |
| Already verified internal phone number | An already verified, 11-digit number starting with `1`, with no punctuation. |
| Verification confirmation              | Type `YES` only if that phone has already been verified.                     |
| Customer account label                 | A recognizable name for the dedicated test account.                          |
| Hosted WorkOS sign-in hostname         | The hostname recorded during hosted sign-in.                                 |

**The utility does not verify a phone number.** 
It records an existing verification precondition for this local test.
WorkOS email verification does not establish UAD phone verification.
If that precondition has not been satisfied, stop here rather than marking it
verified.

The utility creates a local UAD user, a customer account, and active owner and
validator memberships.
It prints the generated IDs and writes:

- Durable account records: `C:\Users\grego\projects\uad-3-6-validation\data\customer-validation.sqlite3`
- Browser-test expectations: `C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r1\s1\customer-profile.json`

No validation cycle is created.
The utility refuses to overwrite a completed profile or replace an 
already-linked identity.
For subsequent sign-ins, reuse the existing records.

## 6. Open account validation

Return to [the running UAD application](http://localhost:4000/) and refresh the
page.
Sign in again if the session has expired.

Use the eligible customer-account link or the account-specific Run Validation
action.
Confirm that the page shows:

- The expected user and customer account.
- The operating mode resolved by UAD policy.
- A **New validation cycle** action.

Open UAD through its HTTP address.
Double-clicking `C:\Users\grego\projects\uad-3-6-validation\site\index.html`
opens a local HTML file and does not provide the running application's
authenticated workflow.

IT-64R1S1 covers account entry.
Submitting a report and creating a durable validation cycle are subsequent
integration work; the entry page identifies that limitation.

## 7. Run the browser sign-in test

In the second Command Prompt, run:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
set "UAD_IT64_CUSTOMER_PROFILE=C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\it_64\r1\s1\customer-profile.json"
".venv\Scripts\python.exe" -B -m pytest tests\test_it_64_r1_s1_reach_account_validation_after_sign_in.py --headed -s -q --tb=short -p no:cacheprovider
```

A visible browser opens. Complete the real hosted sign-in using the same WorkOS user within three minutes. A session in your ordinary browser does not necessarily sign in the test browser.

The test checks the verified user, customer membership, operating mode, validation-page access, and that sign-in alone did not create a cycle. This is an interactive integration test.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused | Keep the server terminal running on port 4000. |
| `/login` reports missing settings | Start the server with `run_server.py`; settings in a separate test process do not configure the server. |
| Redirect URI error | Match `http://localhost:4000/auth/callback` exactly in WorkOS and the launcher. |
| Authenticated user has no local account | Run the setup utility with the correct WorkOS user ID and the same local store used by the server. |
| Test cannot find its profile | Confirm the full profile path and set `UAD_IT64_CUSTOMER_PROFILE` in the terminal running pytest. |
| Hosted sign-in hostname assertion fails | Compare the profile's hostname with the actual hosted page's hostname. |
| Session stops working after server restart | Sign in again; the launcher generates a new cookie password unless one is supplied. Local account records remain saved. |

If using the optional `UAD_CUSTOMER_STORE` override, give the setup utility and server the same value. The default paths above need no override.



## OTDD Feature Numbering
### Basics
**Rules**
1. IT   :   Iteration
2. "-"  :   '-' separator  
3. nn   :   Iteration Number from 1 to 99
4. 'R'  :   Rule marker
5. n    :   Rule Number within the feature file from 1 to 9

**Scenarios**
6. 'S'  :   Scenario marker
7. n    :   Scenario Number within the rule from 1 to 9

## Details
- Each iteration spans the work selected from one feature file and may contain one or more rules.
- Iteration Number is cumulatively incremented across the project
- Rule Number is incremented for each rule in the file
- "IT-99R1" is the 99th iteration of the project, the first Rule in the feature file we are implementing
- "IT-99R1S1" is the first scenario in the first rule of the 99th iteration

## Expansion
- If more than 99 iterations are needed, the iteration number is incremented to 1NN
- "IT-100R1" is the 100th iteration of the project, the first Rule in the feature file we are implementing
- If more than 9 rules in one feature file N is incremented to 1N
- "IT-199R10S1" is the first scenario in the 10th rule of the 199th iteration
- If more than 9 scenarios in one rule N is incremented to 1N
- "IT-199R10S10" is the tenth scenario in the 10th rule of the 199th iteration
Note: If work is properly divided, these expansions are not needed.
Except a huge project may need more than 99 iterations.

## Break-ups
When a feature file needs to be broken up into smaller pieces, the OTDD Feature Numbering will
take on an alphabetic suffix.

@IT-22R1-A
@IT-22R1-B