import asyncio
import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import private_store as store
from app.daily_reports import SAST, DailyReport, publish
from app.main import app
from app.mcp_server import app as old_bridge
from app.private_auth import COOKIE, ORIGIN, digest
from app.report_bridge import RESOURCE, SCOPE, provider

PASSWORD = "local-test-only-long-password"
CALLBACK = "https://chatgpt.com/connector_platform_oauth_redirect"


@pytest.fixture
def private_db(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "private.db"))
    monkeypatch.setenv("EDGE_TEST_SQLITE", "1")
    monkeypatch.delenv("RENDER", raising=False)
    token = secrets.token_urlsafe(32)
    monkeypatch.setenv("EDGE_ACTIVATION_SHA256", digest(token))
    monkeypatch.setenv("EDGE_ACTIVATION_EXPIRES", str(int(time.time()) + 3600))
    yield token
    store._engine_for.cache_clear()


@pytest.fixture
def owner(private_db):
    client = TestClient(app, base_url=ORIGIN)
    response = client.post(
        "/auth/activate",
        json={"password": PASSWORD, "activation_token": private_db},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200, response.text
    me = client.get("/auth/me").json()
    client.headers.update({"Origin": ORIGIN, "X-Edge-CSRF": me["csrf"]})
    return client


def report_data():
    now = datetime.now(SAST)
    return {
        "schema_version": 1,
        "report_date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "status": "NO_DATA",
        "summary": "Synthetic local test — never a real prediction",
        "analysis": "No prices or predictions were researched for this test.",
        "limitations": "Local test only.",
        "previous_day_review": "Unavailable.",
        "sources": [
            {
                "name": "Test source",
                "url": "https://example.com/",
                "status": "not_checked",
                "note": "Synthetic test",
            }
        ],
    }


def oauth_grant(owner):
    metadata = owner.get("/.well-known/oauth-authorization-server").json()
    assert metadata["code_challenge_methods_supported"] == ["S256"]
    registration = owner.post(
        "/register",
        json={
            "redirect_uris": [CALLBACK],
            "client_name": "Private test publisher",
            "scope": SCOPE,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
        },
    )
    assert registration.status_code == 201, registration.text
    client = registration.json()
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    auth = owner.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client["client_id"],
            "redirect_uri": CALLBACK,
            "state": "test-state",
            "scope": SCOPE,
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert auth.status_code == 302, auth.text
    request_id = parse_qs(urlsplit(auth.headers["location"]).query)["request"][0]
    approval = owner.post("/auth/consent", json={"request_id": request_id, "approve": True})
    assert approval.status_code == 200, approval.text
    callback = parse_qs(urlsplit(approval.json()["redirect"]).query)
    assert callback["state"] == ["test-state"]
    return client, {
        "grant_type": "authorization_code",
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "code": callback["code"][0],
        "code_verifier": verifier,
        "redirect_uri": CALLBACK,
        "resource": RESOURCE,
    }


@pytest.mark.parametrize(
    "path",
    [
        "/v1/events/today",
        "/v1/system/status",
        "/v1/web-intelligence/scan",
        "/v1/research-reports",
        "/v1/research-reports/latest",
        "/auth/me",
        "/openapi.json",
        "/docs",
    ],
)
def test_anonymous_private_routes_denied(private_db, path):
    response = TestClient(app, base_url=ORIGIN).get(path)
    assert response.status_code == 401
    assert response.json() == {"detail": "Sign-in required"}
    assert "no-store" in response.headers["cache-control"]


def test_landing_and_health_do_not_leak_data(private_db):
    client = TestClient(app, base_url=ORIGIN)
    assert client.get("/", follow_redirects=False).status_code == 303
    health = client.get("/health").json()
    assert health["private_access"] is True
    assert "stored_observations" not in health and "qualified" not in health
    assert "default-src 'self'" in client.get("/login").headers["content-security-policy"]


def test_activation_rejects_wrong_token_and_origin(private_db):
    client = TestClient(app, base_url=ORIGIN)
    body = {"password": PASSWORD, "activation_token": "x" * 40}
    assert client.post("/auth/activate", json=body).status_code == 403
    assert client.post("/auth/activate", json=body, headers={"Origin": ORIGIN}).status_code == 403
    assert store.get("owner") is None


def test_activation_one_owner_and_cookie_flags(owner, private_db):
    assert owner.get("/auth/me").status_code == 200
    assert not store.get("owner")["password_hash"].endswith(PASSWORD)
    response = owner.post(
        "/auth/activate", json={"password": PASSWORD, "activation_token": private_db}
    )
    assert response.status_code == 409
    response = owner.post("/auth/login", json={"password": PASSWORD})
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    assert "Domain=" not in cookie


def test_logout_revokes_session(owner):
    token = owner.cookies.get(COOKIE)
    assert owner.post("/auth/logout").status_code == 200
    owner.cookies.set(COOKIE, token)
    assert owner.get("/v1/research-reports/latest").status_code == 401


@pytest.mark.parametrize("headers", [{"Origin": "https://evil.example"}, {"X-Edge-CSRF": "wrong"}])
def test_csrf_protects_writes(owner, headers):
    assert owner.post("/auth/revoke-publisher", headers=headers).status_code == 403


def test_login_throttles_persistently(private_db):
    client = TestClient(app, base_url=ORIGIN)
    for _ in range(12):
        assert (
            client.post(
                "/auth/login", json={"password": "wrong"}, headers={"Origin": ORIGIN}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/auth/login", json={"password": "wrong"}, headers={"Origin": ORIGIN}
        ).status_code
        == 429
    )


def test_missing_database_fails_closed(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    client = TestClient(app, base_url=ORIGIN)
    client.cookies.set(COOKIE, "x" * 43)
    assert client.get("/v1/research-reports/latest").status_code == 503
    assert client.get("/health").status_code == 200


def test_no_sqlite_on_render(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "render.db"))
    monkeypatch.setenv("EDGE_TEST_SQLITE", "1")
    monkeypatch.setenv("RENDER", "true")
    store._engine_for.cache_clear()
    with pytest.raises(RuntimeError):
        store.engine()


def test_report_is_private_durable_idempotent_and_not_a_portfolio(owner):
    report = DailyReport.model_validate(report_data())
    receipt = publish(report)
    assert receipt["stored"] and not receipt["duplicate"]
    assert publish(report)["duplicate"]
    store._engine_for.cache_clear()  # Simulate a new process, no in-memory data.
    latest = owner.get("/v1/research-reports/latest").json()
    assert latest["report"]["summary"] == report.summary
    assert latest["research_only"] is True
    with pytest.raises(Exception) as conflict:
        publish(report.model_copy(update={"summary": "Different original report"}))
    assert conflict.value.status_code == 409
    assert TestClient(app, base_url=ORIGIN).get("/v1/research-reports/latest").status_code == 401


def test_source_and_report_validation():
    bad = report_data()
    bad["sources"][0]["url"] = "javascript:alert(1)"
    with pytest.raises(ValidationError):
        DailyReport.model_validate(bad)
    bad = report_data()
    bad["generated_at"] = "2026-09-19T00:00:00"
    with pytest.raises(ValidationError):
        DailyReport.model_validate(bad)
    bad = report_data()
    bad["sources"][0]["status"] = "checked"
    with pytest.raises(ValidationError):
        DailyReport.model_validate(bad)
    bad = report_data()
    bad["status"] = "QUALIFIED_PORTFOLIO"
    with pytest.raises(ValidationError):
        DailyReport.model_validate(bad)


def test_future_reports_rejected(owner):
    future = datetime.now(SAST) + timedelta(days=1)
    report = report_data()
    report.update(report_date=future.date().isoformat(), generated_at=future.isoformat())
    with pytest.raises(Exception) as invalid:
        publish(DailyReport.model_validate(report))
    assert invalid.value.status_code == 422


def test_oversized_request_rejected(private_db):
    response = TestClient(app, base_url=ORIGIN).post("/auth/login", content="x" * 96001)
    assert response.status_code == 413
    assert "no-store" in response.headers["cache-control"]


def test_sdk_oauth_pkce_resource_replay_and_scope(owner):
    client, form = oauth_grant(owner)
    wrong = owner.post("/token", data={**form, "code_verifier": "wrong"})
    assert wrong.status_code == 400
    wrong_resource = owner.post("/token", data={**form, "resource": "https://other.example/mcp"})
    assert wrong_resource.status_code == 400
    tokens = owner.post("/token", data=form)
    assert tokens.status_code == 200, tokens.text
    access = tokens.json()["access_token"]
    assert tokens.json()["scope"] == SCOPE
    assert owner.post("/token", data=form).status_code == 400
    grant = asyncio.run(provider.load_access_token(access))
    assert grant.resource == RESOURCE and grant.subject == "owner"
    stranger = TestClient(app, base_url=ORIGIN)
    # An upload-only OAuth token cannot be used as the owner's session on ANY ordinary API.
    assert (
        stranger.get(
            "/v1/research-reports/latest", headers={"Authorization": "Bearer " + access}
        ).status_code
        == 401
    )
    refresh = {
        "grant_type": "refresh_token",
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": tokens.json()["refresh_token"],
        "resource": RESOURCE,
    }
    rotated = owner.post("/token", data=refresh)
    assert rotated.status_code == 200, rotated.text
    assert owner.post("/token", data=refresh).status_code == 400  # reuse revokes the family
    assert asyncio.run(provider.load_access_token(rotated.json()["access_token"])) is None


def test_oauth_owner_can_revoke(owner):
    _, form = oauth_grant(owner)
    access = owner.post("/token", data=form).json()["access_token"]
    assert asyncio.run(provider.load_access_token(access)) is not None
    assert owner.post("/auth/revoke-publisher").status_code == 200
    assert asyncio.run(provider.load_access_token(access)) is None


def test_foreign_redirect_registration_denied(private_db):
    client = TestClient(app, base_url=ORIGIN)
    response = client.post(
        "/register", json={"redirect_uris": ["https://evil.example/callback"], "scope": SCOPE}
    )
    assert response.status_code == 400


def test_old_anonymous_bridge_cannot_forward():
    client = TestClient(old_bridge)
    assert client.get("/health").json()["anonymous_bridge"] == "disabled"
    assert client.post("/mcp", json={"method": "tools/call"}).status_code == 410


def test_mcp_upload_end_to_end_and_no_read_tools(owner):
    _, form = oauth_grant(owner)
    access = owner.post("/token", data=form).json()["access_token"]
    with TestClient(app, base_url=ORIGIN) as publisher:
        headers = {
            "Authorization": "Bearer " + access,
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-06-18",
        }
        anonymous = publisher.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert anonymous.status_code == 401
        listed = publisher.post(
            "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        assert listed.status_code == 200, listed.text
        names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        assert names == {"get_report_delivery_status", "publish_daily_report"}
        response = publisher.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "publish_daily_report", "arguments": {"report": report_data()}},
            },
        )
        assert response.status_code == 200, response.text
        assert not response.json()["result"].get("isError"), response.text
    assert owner.get("/v1/research-reports/latest").json()["report"]["status"] == "NO_DATA"
