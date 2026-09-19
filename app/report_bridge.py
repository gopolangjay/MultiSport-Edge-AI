"""OAuth report publisher. The MCP SDK handles PKCE and the OAuth protocol.

Owner consent grants only reports:publish. No report-reading, betting, deployment,
repository, or account-management tool is exposed to this connection.
"""

from __future__ import annotations

import re
import secrets
import time
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, HTTPException
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import BaseModel, ConfigDict, Field

from app import private_store as store
from app.daily_reports import DailyReport, publish
from app.private_auth import ORIGIN, digest

SCOPE = "reports:publish"
RESOURCE = ORIGIN + "/mcp"
router = APIRouter()


def allowed_redirect(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "chatgpt.com" or parts.query or parts.fragment:
        return False
    return parts.path == "/connector_platform_oauth_redirect" or bool(
        re.fullmatch(r"/connector/oauth/[a-zA-Z0-9_-]{1,128}", parts.path)
    )


class ReportOAuthProvider:
    async def get_client(self, client_id: str):
        record = store.get("client:" + digest(client_id))
        return OAuthClientInformationFull.model_validate(record) if record else None

    async def register_client(self, client_info: OAuthClientInformationFull):
        if not client_info.redirect_uris or not all(
            allowed_redirect(str(url)) for url in client_info.redirect_uris
        ):
            raise RegistrationError("invalid_redirect_uri", "Only ChatGPT callbacks are allowed")
        if set((client_info.scope or "").split()) - {SCOPE}:
            raise RegistrationError("invalid_client_metadata", "Only reports:publish is supported")
        store.create("client:" + digest(client_info.client_id), client_info.model_dump(mode="json"))

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams):
        if params.resource != RESOURCE:
            raise AuthorizeError("invalid_target", "Report publisher resource required")
        if params.scopes != [SCOPE] or not allowed_redirect(str(params.redirect_uri)):
            raise AuthorizeError("invalid_scope", "Only report publishing may be authorized")
        request_id = secrets.token_urlsafe(32)
        store.create(
            "oauth:pending:" + digest(request_id),
            {"client_id": client.client_id, "params": params.model_dump(mode="json")},
            int(time.time()) + 600,
        )
        return ORIGIN + "/auth/consent?request=" + request_id

    async def load_authorization_code(self, client, authorization_code):
        data = store.get("oauth:code:" + digest(authorization_code))
        if not data or data["client_id"] != client.client_id:
            return None
        return AuthorizationCode(code=authorization_code, **data)

    async def exchange_authorization_code(self, client, authorization_code):
        data = store.consume("oauth:code:" + digest(authorization_code.code))
        if not data or data["client_id"] != client.client_id or data["resource"] != RESOURCE:
            raise TokenError("invalid_grant", "Code expired or already used")
        family = secrets.token_urlsafe(24)
        expires = int(time.time()) + 30 * 86400
        store.create("oauth:family:" + family, {"expires_at": expires}, expires)
        return self.issue(client.client_id, family, expires)

    def issue(self, client_id: str, family: str, expires: int):
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = int(time.time())
        common = {
            "client_id": client_id,
            "scopes": [SCOPE],
            "resource": RESOURCE,
            "subject": "owner",
            "family": family,
        }
        store.create(
            "oauth:access:" + digest(access),
            {**common, "expires_at": min(now + 3600, expires)},
            min(now + 3600, expires),
        )
        store.create("oauth:refresh:" + digest(refresh), {**common, "expires_at": expires}, expires)
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=min(3600, expires - now),
            refresh_token=refresh,
            scope=SCOPE,
        )

    async def load_refresh_token(self, client, refresh_token):
        key = digest(refresh_token)
        used = store.get("oauth:used:" + key)
        if used:
            store.consume("oauth:family:" + used["family"])
            return None
        data = store.get("oauth:refresh:" + key)
        if (
            not data
            or data["client_id"] != client.client_id
            or not store.get("oauth:family:" + data["family"])
        ):
            return None
        return RefreshToken(token=refresh_token, **{k: v for k, v in data.items() if k != "family"})

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        if scopes != [SCOPE]:
            raise TokenError("invalid_scope", "Only reports:publish is supported")
        key = digest(refresh_token.token)
        data = store.consume("oauth:refresh:" + key)
        if (
            not data
            or data["client_id"] != client.client_id
            or not store.get("oauth:family:" + data["family"])
        ):
            raise TokenError("invalid_grant", "Refresh token already used or revoked")
        store.create("oauth:used:" + key, {"family": data["family"]}, data["expires_at"])
        return self.issue(client.client_id, data["family"], data["expires_at"])

    async def load_access_token(self, token):
        data = store.get("oauth:access:" + digest(token))
        if (
            not data
            or data["resource"] != RESOURCE
            or data["scopes"] != [SCOPE]
            or not store.get("oauth:family:" + data["family"])
        ):
            return None
        return AccessToken(
            token=token, claims={"iss": ORIGIN}, **{k: v for k, v in data.items() if k != "family"}
        )

    async def revoke_token(self, token):
        for kind in ("access", "refresh"):
            data = store.get(f"oauth:{kind}:" + digest(token.token))
            if data:
                store.consume("oauth:family:" + data["family"])

    async def exchange_identity_assertion(self, client, params):
        raise TokenError("unsupported_grant_type", "Owner consent is required")


provider = ReportOAuthProvider()
mcp = MCPServer(
    "multisport-private-reports",
    title="MultiSport Private Reports",
    version="1.0.0",
    instructions="Publish bounded original daily research only. Never invent odds or probabilities. "
    "No report-reading, betting, account management or infrastructure access is granted.",
    auth_server_provider=provider,
    auth=AuthSettings(
        issuer_url=ORIGIN,
        resource_server_url=RESOURCE,
        validate_token_resource=True,
        required_scopes=[SCOPE],
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]
        ),
        revocation_options=RevocationOptions(enabled=True),
    ),
)


def require_publisher():
    token = get_access_token()
    if (
        not token
        or token.subject != "owner"
        or token.resource != RESOURCE
        or SCOPE not in token.scopes
    ):
        raise PermissionError("Report publisher authorization required")


@mcp.tool(
    name="get_report_delivery_status",
    description="Harmless connection check; no private report content.",
)
def get_report_delivery_status() -> dict:
    require_publisher()
    store.engine()
    return {
        "ok": True,
        "permission": SCOPE,
        "storage": "private_database",
        "schema_version": 1,
        "delivery_target": "MultiSport-Edge-AI",
        "timezone": "Africa/Johannesburg",
    }


@mcp.tool(
    name="publish_daily_report",
    description=(
        "Store today's original research report privately for the owner. Upload-only; cannot read, "
        "overwrite or qualify betting selections. Return the confirmed date and content hash."
    ),
)
def publish_daily_report(report: DailyReport) -> dict:
    require_publisher()
    return publish(report)


bridge_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    max_request_body_size=96_000,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[urlsplit(ORIGIN).netloc],
        allowed_origins=[ORIGIN],
    ),
)


class Consent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=32, max_length=128)
    approve: bool


@router.get("/auth/consent-details")
def consent_details(request: str):
    pending = store.get("oauth:pending:" + digest(request))
    if not pending:
        raise HTTPException(400, "Connection request expired. Start the connection again.")
    return {
        "scope": SCOPE,
        "destination": "Your private MultiSport database",
        "can_read_reports": False,
        "can_place_bets": False,
    }


@router.post("/auth/consent")
def consent(body: Consent):
    pending = store.consume("oauth:pending:" + digest(body.request_id))
    if not pending:
        raise HTTPException(400, "Connection request expired or already used")
    params = AuthorizationParams.model_validate(pending["params"])
    result = {"state": params.state, "iss": ORIGIN}
    if body.approve:
        code = secrets.token_urlsafe(32)
        expires = int(time.time()) + 120
        data = AuthorizationCode(
            code=code,
            client_id=pending["client_id"],
            expires_at=expires,
            subject="owner",
            **params.model_dump(exclude={"state"}),
        )
        store.create(
            "oauth:code:" + digest(code), data.model_dump(mode="json", exclude={"code"}), expires
        )
        result["code"] = code
    else:
        result["error"] = "access_denied"
    return {
        "redirect": str(params.redirect_uri)
        + "?"
        + urlencode({k: v for k, v in result.items() if v is not None})
    }


@router.get("/auth/publishing-status")
def publishing_status():
    return {
        "connected": bool(store.recent("oauth:family:", 1)),
        "scope": SCOPE,
        "mcp_url": RESOURCE,
        "note": "Connection consent is not proof that the scheduled task has published a report.",
    }
