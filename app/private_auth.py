"""Single-owner sessions, no public registration and no built-in passwords."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from app import private_store as store

ORIGIN = os.getenv("EDGE_PUBLIC_ORIGIN", "https://multisport-edge-ai.onrender.com").rstrip("/")
COOKIE = "__Host-edge_session"
SESSION_SECONDS = 12 * 60 * 60
router = APIRouter()
PUBLIC = {
    "/health",
    "/ready",
    "/login",
    "/activate",
    "/auth/login",
    "/auth/activate",
    "/robots.txt",
}
OAUTH_PUBLIC = {
    "/authorize",
    "/token",
    "/register",
    "/revoke",
    "/mcp",
    "/mcp/",
    "/.well-known/oauth-authorization-server",
    "/.well-known/oauth-protected-resource/mcp",
}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${hashed}"


def password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(iterations) != 600_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def same_origin(request: Request) -> None:
    if request.headers.get("origin") != ORIGIN:
        raise HTTPException(403, "Same-origin request required")


def throttle(request: Request, action: str, limit: int = 12) -> None:
    """Persistent fixed-window attempt slots; includes a global abuse cap."""
    bucket = int(time.time()) // 900
    ip = request.client.host if request.client else "unknown"
    for identity, capacity in ((digest(ip), limit), ("global", 100)):
        for slot in range(capacity):
            key = f"rate:{action}:{bucket}:{identity}:{slot}"
            if store.create(key, {}, (bucket + 1) * 900):
                break
        else:
            raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")


def session(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE, "")
    if not 32 <= len(token) <= 128:
        return None
    return store.get("session:" + digest(token))


def new_session(response: JSONResponse) -> None:
    token = secrets.token_urlsafe(32)
    store.create(
        "session:" + digest(token),
        {"csrf": secrets.token_urlsafe(32)},
        int(time.time()) + SESSION_SECONDS,
    )
    response.set_cookie(
        COOKIE, token, max_age=SESSION_SECONDS, secure=True, httponly=True, samesite="lax", path="/"
    )


class PrivateAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        try:
            # Body limits apply before validation, including chunked requests.
            if request.method in {"POST", "PUT", "PATCH"}:
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 96_000:
                        return self.headers(
                            JSONResponse({"detail": "Request too large"}, status_code=413)
                        )
                request._body = bytes(body)
            if path in {"/register", "/authorize", "/token", "/revoke"}:
                throttle(request, "oauth", limit=60)
            if path == "/token" and request.method == "POST":
                fields = parse_qs((await request.body()).decode("utf-8"))
                if fields.get("resource") != [ORIGIN + "/mcp"]:
                    return self.headers(JSONResponse({"error": "invalid_target"}, status_code=400))
            is_public = path in PUBLIC or path.startswith("/static/") or path in OAUTH_PUBLIC
            if not is_public:
                current = session(request)
                if current is None:
                    if request.method == "GET" and path in {"/", "/auth/consent"}:
                        target = str(request.url.path)
                        if request.url.query:
                            target += "?" + request.url.query
                        response = RedirectResponse("/login?next=" + quote(target, safe=""), 303)
                    else:
                        response = JSONResponse({"detail": "Sign-in required"}, status_code=401)
                    return self.headers(response)
                request.state.edge_session = current
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    same_origin(request)
                    if not hmac.compare_digest(
                        request.headers.get("x-edge-csrf", ""), current["csrf"]
                    ):
                        raise HTTPException(403, "Invalid CSRF token")
            response = await call_next(request)
        except HTTPException as exc:
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        except Exception:
            # No connection strings, passwords, report text or stack traces in responses.
            response = JSONResponse(
                {"detail": "Private service temporarily unavailable"}, status_code=503
            )
        return self.headers(response)

    @staticmethod
    def headers(response):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' https: data:; connect-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'; base-uri 'none'; object-src 'none'"
        )
        return response


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=128)


class Activation(Login):
    password: str = Field(min_length=15, max_length=128)
    activation_token: str = Field(min_length=32, max_length=128)


@router.get("/login", response_class=HTMLResponse)
@router.get("/activate", response_class=HTMLResponse)
@router.get("/auth/consent", response_class=HTMLResponse)
def auth_page():
    return HTMLResponse((Path(__file__).parent / "templates" / "private-access.html").read_text())


@router.post("/auth/activate")
def activate(body: Activation, request: Request):
    same_origin(request)
    throttle(request, "activate")
    expected = os.getenv("EDGE_ACTIVATION_SHA256", "")
    try:
        expires = int(os.getenv("EDGE_ACTIVATION_EXPIRES", "0"))
    except ValueError:
        expires = 0
    if (
        len(expected) != 64
        or expires <= time.time()
        or not hmac.compare_digest(digest(body.activation_token), expected)
    ):
        raise HTTPException(403, "Activation link invalid or expired")
    if not store.create("owner", {"password_hash": password_hash(body.password)}):
        raise HTTPException(409, "Owner already activated. Sign in instead.")
    store.prune()
    response = JSONResponse({"ok": True})
    new_session(response)
    return response


@router.post("/auth/login")
def login(body: Login, request: Request):
    same_origin(request)
    throttle(request, "login")
    owner = store.get("owner")
    if not owner or not password_matches(body.password, owner["password_hash"]):
        raise HTTPException(401, "Invalid sign-in")
    store.prune()
    response = JSONResponse({"ok": True})
    new_session(response)
    return response


@router.get("/auth/me")
def whoami(request: Request):
    return {"ok": True, "role": "owner", "csrf": request.state.edge_session["csrf"]}


@router.post("/auth/logout")
def logout(request: Request):
    store.consume("session:" + digest(request.cookies.get(COOKIE, "")))
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@router.post("/auth/revoke-publisher")
def revoke_publisher():
    store.remove_prefix("oauth:")
    return {"ok": True, "publishing_connections_revoked": True}


@router.get("/robots.txt")
def robots():
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@router.get("/ready")
def ready():
    # Infrastructure readiness only; never return ownership, reports or credentials.
    from sqlalchemy import text

    with store.engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "private_storage": "available"}
