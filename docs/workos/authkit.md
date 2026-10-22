<!-- llms.txt: https://workos.com/llms.txt -->
<!-- feedback.md: https://workos.com/docs/feedback.md -->

# AuthKit

## Introduction

Integrating AuthKit into your app can be done in less than ten minutes. 
In this guide, we'll walk you through adding a hosted authentication flow to
your application using AuthKit.

In addition to this guide, there are a variety of
[example apps](https://workos.com/docs/authkit/example-apps) 
available to help with your integration.

## Before getting started

To get the most out of this guide, you'll need:

- A [WorkOS account](https://dashboard.workos.com/)
- Your WorkOS [API Key](https://workos.com/docs/glossary/api-key) 
and [Client ID](https://workos.com/docs/glossary/client-id)

***

## (1) Configure your project

Let's add the necessary dependencies and configuration in your WorkOS Dashboard.

### Install dependencies

First, install the Python SDK.

```bash title="Install Python SDK"
pip install workos
```

pip install workos `Flask-WTF`:

```bash title="Install CSRF protection"
pip install Flask-WTF
```

### Configure a redirect URI

A redirect URI is a callback endpoint that WorkOS will redirect to after a
user has authenticated.
This endpoint will exchange the authorization code returned by WorkOS for an
authenticated [User object](https://workos.com/docs/reference/authkit/user).
We'll create this endpoint in the next step.

You can set a redirect URI in the [Applications](https://dashboard.workos.com/environment/applications) section
of the WorkOS Dashboard.
Open your application and go to the **Redirects** tab to add a redirect URI.
We recommend using `http://localhost:3000/callback` as the default here.

WorkOS supports using wildcard characters in Redirect URIs, but not for the
default Redirect URI.
More information about wildcard characters support can be found in the
[Redirect URIs](https://workos.com/docs/sso/redirect-uris/wildcard-characters) guide.


![Dashboard redirect URI](https://images.workoscdn.com/images/b00949fa-b693-4b53-b214-dd06c4efd3e1.png?auto=format\&fit=clip\&q=80)

When users sign out of their application, they will be redirected to your
app's [Sign-out URI](https://workos.com/docs/authkit/sessions#sign-out-uris) which
is configured in the same dashboard area.

### Configure Initiate login URI

Sign-in requests should originate from your application.
In some instances, requests may not begin at your app.
For example, some users might bookmark the hosted sign-in page or they might be
led directly to the hosted sign-in page when clicking on a password reset or
invitation link in an email.

In these cases, AuthKit will detect when a sign-in request did not originate at
your application and redirect to your application's Initiate login URI.
This is an endpoint that you define at your application that redirects users to
sign in using AuthKit.
We'll create this endpoint in the next step.
Password reset and invitation details are preserved through this redirect, so users
continue on to the correct page as long as your Initiate login URI starts an AuthKit
sign-in rather than rendering your own sign-in page.

You can configure the Initiate login URI from your application's **Redirects**
tab in the [Applications](https://dashboard.workos.com/environment/applications)
section of the WorkOS Dashboard.

![Initiate login URI](https://images.workoscdn.com/images/25b53ea7-95ba-48cc-b6e7-ccd1b1bc35eb.png?auto=format\&fit=clip\&q=80)

### Set secrets

To make calls to WorkOS, provide the API key and the client ID.
Store these values as managed secrets and pass them to the SDKs either as
environment variables or directly in your app's configuration depending on your
preferences.

```plain title="Environment variables"
WORKOS_API_KEY='WORKOS_API_KEY_PLACEHOLDER'
WORKOS_CLIENT_ID='client_01M4EG0A3E0KXBYFMMETQFJKXY'
```

> The code examples use your staging API keys when
> [signed in](https://dashboard.workos.com)

***

## (2) Add AuthKit to your app

Let's integrate the hosted authentication flow into your app.

### Set up the frontend

To demonstrate AuthKit, we only need a simple page with links to logging in and out.

:::code-group{title="index.html"}

```html language="html"
<!doctype html>
<html lang="en">
  <head>
    <title>AuthKit example</title>
  </head>
  <body>
    <h1>AuthKit example</h1>
    <p>This is an example of how to use AuthKit with an HTML frontend.</p>
    <p>
      <a href="/login">Sign in</a>
    </p>
    <form action="/logout" method="POST" id="logout-form">
      <input type="hidden" name="_csrf" id="csrf-token" />
      <button type="submit">Sign out</button>
    </form>

    <script>
      // Fetch CSRF token on page load
      fetch('/csrf-token')
        .then((r) => r.json())
        .then((data) => {
          document.getElementById('csrf-token').value = data.csrfToken;
        });
    </script>
  </body>
</html>
```

:::

Clicking the "Sign in" and "Sign out" links should invoke actions on our server,
which we'll set up next.

### Add an Initiate login URI

We'll need an Initiate login URI to direct users to sign in (or sign up) using
AuthKit before redirecting them back to your application.
This endpoint should generate an AuthKit authorization URL server side and
redirect the user to it.

You can use the optional state parameter to encode arbitrary information to help
restore application `state` between redirects.

For this guide we'll be using the `flask` web server for Python.
This guide won't cover how to set up a Flask app, but you can find more
information in the
[Flask documentation](https://flask.palletsprojects.com/en/stable/).

:::code-group{title="server.py"}

```py language="python"
import os

from dotenv import load_dotenv
from flask import Flask, redirect, send_file
from workos import WorkOSClient

load_dotenv()

app = Flask(__name__)

workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"), client_id=os.getenv("WORKOS_CLIENT_ID")
)


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/login")
def login():
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit", redirect_uri="http://localhost:3000/callback"
    )

    return redirect(authorization_url)


if __name__ == "__main__":
    app.run(debug=True, port=3000)
```

:::

> WorkOS will redirect to your
> [Redirect URI](https://workos.com/docs/glossary/redirect-uri) 
> if there is an issue generating an authorization URL.
> Read our [API Reference](https://workos.com/docs/reference) for more details.

### Add a callback endpoint

Next, let's add the callback endpoint (referenced in
[Configure a redirect URI](https://workos.com/docs/authkit/1-configure-your-project/configure-a-redirect-uri)) 
which will exchange the authorization code (valid for 10 minutes) for an 
authenticated User object.

:::code-group{title="server.py"}

```py language="python"
import os

from dotenv import load_dotenv

# +diff-start
from flask import Flask, make_response, redirect, request, url_for

# +diff-end
from workos import WorkOSClient

load_dotenv()

app = Flask(__name__)

workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"), client_id=os.getenv("WORKOS_CLIENT_ID")
)

cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")


@app.route("/login")
def login():
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit", redirect_uri="http://localhost:3000/callback"
    )

    return redirect(authorization_url)


# +diff-start
@app.route("/callback")
def callback():
    code = request.args.get("code")

    try:
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
        )

        # Use the information in auth_response for further business logic.

        response = make_response(redirect("/"))

        return response

    except Exception as e:
        print("Error authenticating with code", e)
        return redirect(url_for("login"))


# +diff-end

if __name__ == "__main__":
    app.run(debug=True, port=3000)
```

:::

## (3) Handle the user session

Session management helper methods are included in our SDKs to make integration easy. For security reasons, sessions are automatically "sealed", meaning they are encrypted with a strong password.

### Create a session password

The SDK requires you to set a strong password to encrypt cookies. This password must be 32 characters long. You can generate a secure password by using the [1Password generator](https://1password.com/password-generator/) or the `openssl` library via the command line:

```bash title="Generate a strong password"
openssl rand -base64 32
```

Then add it to the environment variables file.

```plain title=".env"
WORKOS_API_KEY='WORKOS_API_KEY_PLACEHOLDER'
WORKOS_CLIENT_ID='client_01M4EG0A3E0KXBYFMMETQFJKXY'

# +diff-start
WORKOS_COOKIE_PASSWORD='<your password>'
# +diff-end
```

### Save the encrypted session

Next, use the SDK to authenticate the user and return a password protected session. The refresh token is considered sensitive as it can be used to re-authenticate, hence why the session is encrypted before storing it in a session cookie.

:::code-group{title="server.py"}

```py language="python"
import os

from dotenv import load_dotenv
from flask import Flask, make_response, redirect, request, url_for
from workos import WorkOSClient

load_dotenv()

app = Flask(__name__)

workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"), client_id=os.getenv("WORKOS_CLIENT_ID")
)

cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")


@app.route("/login")
def login():
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit", redirect_uri="http://localhost:3000/callback"
    )

    return redirect(authorization_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    try:
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
            # +diff-start
            session={"seal_session": True, "cookie_password": cookie_password},
            # +diff-end
        )

        response = make_response(redirect("/"))
        # +diff-start
        # store the session in a cookie
        response.set_cookie(
            "wos_session",
            auth_response.sealed_session,
            secure=True,
            httponly=True,
            samesite="lax",
        )
        # +diff-end
        return response

    except Exception as e:
        print("Error authenticating with code", e)
        return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=3000)
```

:::

We should also present some of the user information on our frontend. Let's update the default route to read the session cookie and display user information:

:::code-group{title="server.py"}

```py language="python"
@app.route("/")
def index():
    user_data = ""
    sealed_session = request.cookies.get("wos_session")
    if sealed_session:
        try:
            session = workos.user_management.load_sealed_session(
                sealed_session=sealed_session,
                cookie_password=cookie_password,
            )
            auth_response = session.authenticate()
            if auth_response.authenticated and auth_response.user:
                user = auth_response.user
                user_data = f"Welcome, {user.first_name or ''} {user.last_name or ''}! ({user.email or ''})"
        except Exception:
            pass

    with open("index.html") as f:
        html = f.read()
    return html.replace("{{USER_DATA}}", user_data)
```

:::

And, we should make sure to update the index page to present this info.

:::code-group{title="index.html"}

```html language="html"
<!doctype html>
<html lang="en">
  <head>
    <title>AuthKit example</title>
  </head>
  <body>
    <h1>AuthKit example</h1>
    <!--+diff-start -->
    {{USER_DATA}}
    <!-- +diff-end -->
    <p>This is an example of how to use AuthKit with an HTML frontend.</p>
    <p>
      <a href="/login">Sign in</a>
    </p>
    <form action="/logout" method="POST" id="logout-form">
      <input type="hidden" name="_csrf" id="csrf-token" />
      <button type="submit">Sign out</button>
    </form>

    <script>
      // Fetch CSRF token on page load
      fetch('/csrf-token')
        .then((r) => r.json())
        .then((data) => {
          document.getElementById('csrf-token').value = data.csrfToken;
        });
    </script>
  </body>
</html>
```

:::

### Protected routes

Then, use a decorator to specify which routes should be protected. If the session has expired, use the SDK to attempt to generate a new one.

:::code-group{title="server.py"}

```py language="python"
from dotenv import load_dotenv
import os

# +diff-start
from functools import wraps

# +diff-end
from flask import Flask, redirect, request, make_response, url_for
from workos import WorkOSClient

load_dotenv()

app = Flask(__name__)

workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"), client_id=os.getenv("WORKOS_CLIENT_ID")
)

cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

# +diff-start
# Decorator to check if the user is authenticated. If not, redirect to login
def with_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session = workos.user_management.load_sealed_session(
            sealed_session=request.cookies.get("wos_session"),
            cookie_password=cookie_password,
        )
        auth_response = session.authenticate()
        if auth_response.authenticated:
            return f(*args, **kwargs)

        if (
            auth_response.authenticated is False
            and auth_response.reason == "no_session_cookie_provided"
        ):
            return make_response(redirect("/login"))

        # If no session, attempt a refresh
        try:
            print("Refreshing session")
            result = session.refresh()
            if result.authenticated is False:
                return make_response(redirect("/login"))

            response = make_response(redirect(request.url))
            response.set_cookie(
                "wos_session",
                result.sealed_session,
                secure=True,
                httponly=True,
                samesite="lax",
            )
            return response
        except Exception as e:
            print("Error refreshing session", e)
            response = make_response(redirect("/login"))
            response.delete_cookie("wos_session")
            return response

    return decorated_function


# +diff-end


@app.route("/login")
def login():
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit", redirect_uri="http://localhost:3000/callback"
    )

    return redirect(authorization_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    try:
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
            session={"seal_session": True, "cookie_password": cookie_password},
        )

        response = make_response(redirect("/"))

        # store the session in a cookie
        response.set_cookie(
            "wos_session",
            auth_response.sealed_session,
            secure=True,
            httponly=True,
            samesite="lax",
        )

        return response

    except Exception as e:
        print("Error authenticating with code", e)
        return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=3000)
```

:::

Use the decorator in the route that should only be accessible to logged in users.

:::code-group{title="server.py"}

```py language="python"
@app.route("/dashboard")
@with_auth
def dashboard():
    session = workos.user_management.load_sealed_session(
        sealed_session=request.cookies.get("wos_session"),
        cookie_password=cookie_password,
    )

    response = session.authenticate()

    current_user = response.user if response.authenticated else None

    print(f"User {current_user.first_name} is logged in")

    # Render a dashboard view
```

:::

### Ending the session

Finally, ensure the user can end their session by redirecting them to the logout URL. After successfully signing out, the user will be redirected to your app's Sign-out URI, which is configured in the WorkOS dashboard.

:::code-group{title="server.py"}

```py language="python"
from flask_wtf.csrf import CSRFProtect, generate_csrf

csrf = CSRFProtect(app)

# Configure secret key and CSRF field name for CSRF
app.config['SECRET_KEY'] = 'replace-me-with-a-real-secret'
app.config['WTF_CSRF_FIELD_NAME'] = '_csrf'

# Endpoint to get CSRF token for forms
@app.route("/csrf-token")
def csrf_token():
    return jsonify({'csrfToken': generate_csrf()})

@app.route("/logout", methods=["POST"])
def logout():
    session = workos.user_management.load_sealed_session(
        sealed_session=request.cookies.get("wos_session"),
        cookie_password=cookie_password,
    )
    url = session.get_logout_url()

    # After log out has succeeded, the user will be redirected to your
    # app homepage which is configured in the WorkOS dashboard
    response = make_response(redirect(url))
    response.delete_cookie("wos_session")

    return response
```

:::

> **Note:** <strong>CSRF Protection:</strong> The logout endpoint uses POST to prevent
> unintended logouts from browser prefetching. CSRF protection with
> <code>Flask-WTF</code> prevents cross-site request forgery attacks.
> Flask-WTF automatically validates CSRF tokens on POST requests when
> configured with <code>CSRFProtect</code>.

> If you haven't configured a [Sign-out URI](https://workos.com/docs/authkit/sessions#sign-out-uris) in the WorkOS dashboard, users will see an error when logging out.

## Validate the authentication flow

To test all of this out, start your server with `python server.py`, navigate to `localhost:3000`, and sign up for an account.

You can then sign in with the newly created credentials and see the user listed in the **Users** section of the [WorkOS Dashboard](https://dashboard.workos.com).

![Dashboard showing newly created user](https://images.workoscdn.com/images/54fa6e6c-4c6f-4959-9301-344aeb4eeac8.png?auto=format\&fit=clip\&q=80)
