# Private daily report delivery

The main application is **default-deny**. There is no public registration and no
authentication-disable switch. `/health` is liveness-only; `/ready` reports storage
readiness without private data. Dashboard, reports, API, documentation, collector
and observation endpoints all require the owner's authenticated session.

## Owner activation

Configure the existing service, not a new paid resource:

- `DATABASE_URL`: existing Render Postgres **internal** connection string.
- `EDGE_PUBLIC_ORIGIN`: `https://multisport-edge-ai.onrender.com`.
- `EDGE_ACTIVATION_SHA256`: SHA-256 of a cryptographically random, 256-bit activation secret.
- `EDGE_ACTIVATION_EXPIRES`: expiry Unix timestamp; use a short initial window.

Send the secret only to the owner using `/activate#<secret>`. It is a URL fragment,
not an HTTP query parameter. Do not log it, commit it, store it in a scheduled task,
or put it in an APK. The user sets their own password (minimum 15 characters).
Atomic creation of one `owner` record prevents a second registration; the initial
secret does not reset or replace an existing owner. After activation, remove the
activation environment variables when convenient. Forgotten passwords require an
explicit administrator-assisted recovery; never delete the database to reset access.

Passwords use salted PBKDF2-HMAC-SHA256 with 600,000 iterations. Random sessions
are stored only as hashes, expire after 12 hours and use a Secure, HttpOnly,
host-only cookie. Mutations require the exact origin and a session-bound CSRF
token. Login/activation/OAuth attempt limits persist in the database. Private
responses are no-store and noindex; report text is rendered as text, not HTML.
The database is mandatory: unavailable storage yields 503, never public or
in-memory fallback. SQLite is allowed only by the explicit test setting and never
on Render. This is access control, not a claim of end-to-end encryption against
the hosting provider or an independent security audit.

## Connect ChatGPT

MCP URL: `https://multisport-edge-ai.onrender.com/mcp`.

Use OAuth (dynamic client registration), then sign in as the owner and approve
`reports:publish`. Supported callbacks are the documented HTTPS ChatGPT callback
and callback-ID-specific paths; other origins are rejected. The MCP SDK handles
client authentication and S256 PKCE. The database binds each code to the exact
client, callback and resource. Codes expire after two minutes and are consumed
atomically. Access tokens expire after one hour; refresh tokens rotate and expire
after 30 days from consent. Reusing a refresh token revokes its grant family.
The dashboard's Disconnect button revokes publishing grants immediately.

The connector exposes only:

1. `get_report_delivery_status`: harmless authenticated connection test, no reports.
2. `publish_daily_report`: upload-only, one original report per SAST date. No reads,
   overwrites, betting, account administration or infrastructure access.

The legacy MCP service returns 410; it never forwards anonymous private data.
Do not put backend credentials into that old service to restore anonymous access.

## Scheduled task handoff

Keep task `6aade39083e481918d12c3d90e44ca74` at 00:00 Africa/Johannesburg.
**The connection is not complete merely because the code is deployed.** First
the owner must activate their account and connect the OAuth app. Then successfully
call `get_report_delivery_status` from the actual ChatGPT connection before
updating the existing task to depend on it. Do not create a duplicate automation.

Preserve the existing research and source-access restrictions. Add private
publication after research with these fields (see the published tool schema):

- `schema_version`: 1
- `report_date`: current SAST YYYY-MM-DD
- `generated_at`: actual timezone-aware generation timestamp
- `status`: `NO_QUALIFIED_PORTFOLIO`, `RESEARCH_SHORTLIST`, or `NO_DATA`
- `summary`, `analysis`, `limitations`, `previous_day_review`: original text
- `sources`: bounded list of name, HTTPS URL, check status, actual `checked_at`
  timestamp (required for checked/partial), and note

Publish only the user's bounded original report, not bulk extracted tables. Never
invent prices, source checks or probabilities. A report does not automatically
enter the odds/qualification pipeline. Read back the tool's date/hash receipt
before telling the user that the app was updated. Identical retries are accepted;
a different report for a saved date returns a conflict, preserving original picks.
On failure, deliver here and explicitly say private app delivery failed. No public
GitHub, deployment/environment-variable relay, logs, or open endpoint fallback.

The current task must remain chat-only until the OAuth connector is available.
This repository contains code and synthetic tests, **not private research reports**.

## Verification and operations

- `python -m ruff check .`
- `python -m pytest -q`: covers sessions, CSRF, database failure, duplicate reports,
  timestamp/source validation, OAuth/PKCE, token replay, upload-only scope and MCP upload.
- Verify anonymous API access is 401, `/` redirects to sign-in, `/ready` is 200,
  `/mcp` without bearer auth is 401, and the old bridge is 410.
- The Android update uses the HTTPS dashboard and its cookies. Install the new APK;
  old APKs cannot bypass the new server-side access checks.
- Check database retention/expiry separately. A free Render Postgres instance can
  expire; deployment does not automatically extend it or add paid services.

References: [OpenAI MCP authentication](https://developers.openai.com/plugins/build/auth),
[OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
