# Android V2 production acceptance gate

A build is accepted only when all of the following hold:

1. The APK has `INTERNET` permission and cleartext HTTP is disabled.
2. The local WebView UI reaches the fixed production origin through the native HTTPS bridge; file-origin CORS is not relied upon.
3. `/health`, `/v1/events/today`, `/v1/system/status`, and `/v1/web-intelligence/scan` all return successful JSON to the installed-app UI.
4. The Events response populates sport filters, event cards, match details, and provider `home_logo`/`away_logo` images when supplied.
5. Scanner bookmaker counts use the backend `bookmaker_counts` contract and never fabricate odds or confidence.
6. Multi remains empty unless the backend returns a genuinely qualified portfolio.
7. CI, Gradle debug APK build, package/signature checks, ZIP integrity, and artifact inspection pass.

The Android bridge only permits `/health` and `/v1/*` requests on `https://multisport-edge-ai.onrender.com`.
