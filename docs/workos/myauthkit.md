# AuthKit setup for UAD with FastAPI and Uvicorn

This guide adapts the WorkOS Python documentation to the UAD application.
FastAPI defines the application and HTTP routes. Uvicorn runs the application.
WorkOS AuthKit provides the hosted authentication service.

This document describes the existing integration and the remaining work needed
for a complete browser sign-in and sign-out flow. Saving it does not change
application behavior or WorkOS settings.

## Application files

Project root: `C:\Users\grego\projects\uad-3-6-validation`

| File                                                                                              | Purpose                                                                         |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `C:\Users\grego\projects\uad-3-6-validation\app\main.py`                                          | FastAPI application, WorkOS callback, session checks, and local account linking |
| `C:\Users\grego\projects\uad-3-6-validation\pyproject.toml`                                       | Application and development dependencies                                        |
| `C:\Users\grego\projects\uad-3-6-validation\run_workos_tests.py`                                  | Supplies child-process configuration and checks hosted WorkOS before regression |
| `C:\Users\grego\projects\uad-3-6-validation\tests\test_it_2_r5_s1_workos_authkit_availability.py` | Live hosted AuthKit availability prerequisite                                   |

Flask and Flask-WTF are not required for this FastAPI integration.

## Install dependencies

Run these commands in Windows Command Prompt:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
".venv\Scripts\python.exe" -m pip install -e ".[dev]"
".venv\Scripts\python.exe" -m pip check
```

The project declares FastAPI, Uvicorn, WorkOS, Pydantic, Pydantic Settings,
and python-dotenv. Installing the last two does not automatically load settings
or environment files. The authentication code currently uses `os.getenv`.

Installation updates the virtual environment and may update package metadata.
Run ```.venv\Scripts\python.exe -m pip check``` from the project root to check dependency compatibility.
An expected successful dependency check reports `No broken requirements found.`

## Configuration values

Use credentials from the intended WorkOS environment.
Do not mix a staging client ID with a production API key, or a production client
ID with a production API key.

| Variable                 | Purpose                                       | Required by availability test | Required by current callback |
|--------------------------|-----------------------------------------------|-------------------------------|------------------------------|
| `WORKOS_CLIENT_ID`       | Identifies the WorkOS application             | Yes                           | Yes                          |
| `WORKOS_REDIRECT_URI`    | Exact registered application callback URL     | Yes                           | Used when starting sign-in   |
| `WORKOS_API_KEY`         | Authenticates server-side WorkOS API requests | No                            | Yes                          |
| `WORKOS_COOKIE_PASSWORD` | Protects the sealed browser session           | No                            | Yes                          |

Use a strong cookie password meeting the installed WorkOS SDK's requirements;
the Python quickstart specifies at least 32 characters. Keep it stable across
application restarts and shared by application instances that read the same
session cookies. Do not generate a new password for every request.

Never place API keys, cookie passwords, access tokens, refresh tokens, or full
environment dumps in documentation, fixtures, request examples, or Git commits.
Client IDs and callback URLs are configuration identifiers, not API secrets.

## Register application URLs in WorkOS

The current application callback route is `GET /auth/callback`.
For a development application served at `http://localhost:8000`, register:

```text
http://localhost:8000/auth/callback
```

Set `WORKOS_REDIRECT_URI` to that exact value. Scheme, hostname, port, path,
and trailing slash must agree. `localhost` and `127.0.0.1` are different hosts.
This document does not establish what is saved in your WorkOS account.

WorkOS also supports an Initiate login URI and a Sign-out URI:

| Setting | Meaning | UAD implementation status |
| --- | --- | --- |
| Redirect URI | Callback that receives an authorization code | `/auth/callback` exists |
| Initiate login URI | Application endpoint that starts hosted AuthKit sign-in | A dedicated route remains to be implemented |
| Sign-out URI | Public destination after WorkOS signs the user out | Choose a public application page when implementing logout |

A proposed Initiate login route is `/auth/login`. Do not register it as a
working endpoint until the application implements and tests it. A Sign-out URI
is the destination after logout, not the endpoint that performs logout.

[WorkOS application setup](https://workos.com/docs/authkit/vanilla/python)

## Start the existing FastAPI application

From a process that already has the four application variables, run:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`app.main:app` selects the FastAPI object in the existing application module.
Use the browser hostname that matches the registered callback, for example
`http://localhost:8000/`.

The test launcher only launches pytest. It does not configure a separately
started Uvicorn process. If configuration is supplied by a Python launcher,
that launcher must also start Uvicorn with the configured child environment.

Python can construct an environment mapping and pass it through
`subprocess.run(..., env=environment)`. The child receives those values; the
parent Command Prompt does not. Closing the child does not persist them to disk.

## Existing authentication flow

The following behavior was observed in the application source when this guide
was prepared:

1. Middleware intercepts `POST /validate/uad36`.
2. Missing client ID or redirect URI produces an HTTP 503 response.
3. The middleware uses `WorkOSClient` and checks the `wos_session` cookie.
4. An unauthenticated request is redirected to an authorization URL generated
   by `user_management.get_authorization_url` with `provider="authkit"`.
5. WorkOS returns the browser to `/auth/callback` with an authorization code.
6. The callback calls `user_management.authenticate_with_code`, seals the
   authentication response, sets the session cookie, and redirects to `/`.
7. A later protected request must resolve the verified WorkOS identity to a
   local UAD account. An unlinked identity is redirected to `/account/setup`.
8. `POST /account/setup` creates or reuses the linked local account.

WorkOS authenticates the identity. UAD remains responsible for local account
data, company membership authorization, and permission to use appraisal functions.

The current application holds account records and identity links in process
memory. They do not survive restarts and are not shared across Uvicorn workers.
Durable account storage is required before treating this as a deployed account
system. A redirect to `/account/setup` also requires a working browser UI;
the presence of the POST handler alone does not establish that UI.

## Session cookies and local browser testing

The callback currently sets `wos_session` with `HttpOnly`, `Secure`,
`SameSite=Lax`, and path `/`. These are observed application settings.

Because `Secure` cookies are intended for HTTPS, do not assume that a plain
HTTP localhost browser test proves deployed cookie behavior. Verify actual
cookie storage and subsequent authenticated requests in the target browser.
Use a trusted local HTTPS setup when needed. Do not remove `Secure` from
public deployments to work around a development problem.

The current session-check helper rejects unauthenticated sessions; it does not
implement the refresh flow shown in the WorkOS quickstart. Session refresh and
expired-session behavior need explicit implementation and tests.

[WorkOS session documentation](https://workos.com/docs/authkit/sessions)

## Remaining login and logout work

The copied Flask tutorial contains behavior that is not yet fully present in
the UAD application. Implement these through the project's feature, RED, GREEN,
and regression workflow:

- A dedicated GET login route that generates the WorkOS authorization URL.
- Login transaction protection, including generating and validating state.
- Session refresh and recovery when a session expires or is revoked.
- A POST logout route with CSRF protection, SDK-generated WorkOS logout URL,
  and removal of the local session cookie.
- A registered Sign-out URI and verified return to the public application page.
- Preservation of the intended destination after sign-in, where required.

FastAPI does not acquire Flask-WTF's CSRF behavior by installing WorkOS. Use a
FastAPI-compatible design and test rejection of missing or invalid CSRF tokens.
Do not copy Flask decorators or `app.run()` into the FastAPI application.

## Check hosted AuthKit availability

Run:

```bat
cd /d C:\Users\grego\projects\uad-3-6-validation
".venv\Scripts\python.exe" -B run_workos_tests.py
```

Supply the staging client ID and registered callback URL when prompted.
The launcher passes them directly to pytest and checks hosted availability.
Expected successful result: one passing availability test.

That test verifies that WorkOS accepts an authorization request and supplies an
HTTPS sign-in redirect. It does not authenticate a user, exchange a code,
exercise the application callback, or prove the browser session works.

## Run full regression

```bat
".venv\Scripts\python.exe" -B run_workos_tests.py tests data\uad36-test-suite\tests\test_required_data_acceptance.py data\uad36-test-suite\tests\test_required_data_rdf.py --run-canonical-artifact -q --tb=short -p no:cacheprovider
```

The launcher first checks WorkOS. If that check fails, it does not start the
full regression. Review the final test summary and provide GREEN sign-off.
Tests may generate temporary artifacts according to their existing behavior.

## Public test and production deployment

Keep FastAPI and Uvicorn. Use an HTTPS application domain and register the
deployed callback URL in the matching WorkOS environment. A public test system
can use staging credentials; production must use its intended production
environment and separate secrets.

Do not use `--reload` for deployment. Configure the hosting platform or reverse
proxy for HTTPS, process management, and trusted forwarded headers. The exact
startup and network settings depend on the selected host.

Before declaring browser authentication ready, verify sign-in, callback,
local account linkage, authenticated appraisal access, session expiry, refresh,
and logout on that deployed environment. A green availability test and a green
mocked regression suite do not replace these checks.

## References

- [WorkOS Python SDK](https://github.com/workos/workos-python)
- [WorkOS Python AuthKit quickstart](https://workos.com/docs/authkit/vanilla/python)
- [WorkOS sessions](https://workos.com/docs/authkit/sessions)
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn settings](https://www.uvicorn.org/settings/)
