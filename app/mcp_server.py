"""ChatGPT/MCP tool surface for MultiSport Edge AI.

ChatGPT supplies researched observations. The MCP service forwards them to the
main MultiSport Edge backend so the Android dashboard and MCP share one state.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

EDGE_BACKEND_URL = os.getenv(
    "EDGE_BACKEND_URL", "https://multisport-edge-ai.onrender.com"
).rstrip("/")
REQUEST_TIMEOUT = 45.0


def _backend(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{EDGE_BACKEND_URL}{path}"
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        response = client.request(method, url, json=payload)
        response.raise_for_status()
        return response.json()


mcp = MCPServer(
    "multisport-edge-ai",
    title="MultiSport Edge AI",
    description=(
        "Research bridge for evidence-backed Betway and Sportingbet observations. "
        "Research is written to the main MultiSport backend used by the Android app."
    ),
    version="0.2.0",
    instructions=(
        "Never invent fixtures, odds, evidence or confidence. Research current public sources first. "
        "Submit only Betway or Sportingbet observations with source URLs and evidence. "
        "A >=90 analytical-confidence score is a qualification score, not a guaranteed win probability. "
        "If too few selections qualify, return NO_QUALIFIED_PORTFOLIO rather than forcing legs."
    ),
)


@mcp.tool(
    name="get_edge_status",
    description="Read the current scan and portfolio state shown by the MultiSport Android app.",
)
def get_edge_status() -> dict[str, Any]:
    return _backend("GET", "/v1/web-intelligence/scan")


@mcp.tool(
    name="submit_research",
    description=(
        "Submit current evidence-backed Betway or Sportingbet observations to the main backend. "
        "Use after researching current public sports sources."
    ),
)
def submit_research(observations: list[dict[str, Any]]) -> dict[str, Any]:
    if len(observations) > 500:
        raise ValueError("Maximum 500 observations per submission")
    return _backend("POST", "/v1/research-worker/feed", {"observations": observations})


@mcp.tool(
    name="qualify_candidates",
    description="Apply the main backend analytical-confidence/evidence qualification gate.",
)
def qualify_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) > 500:
        raise ValueError("Maximum 500 records per qualification request")
    return _backend("POST", "/v1/web-intelligence/qualify", {"records": records})


@mcp.tool(
    name="build_edge_portfolio",
    description=(
        "Build the main backend correlation-controlled 10-15 leg portfolio targeting 1.45-1.60."
    ),
)
def build_edge_portfolio(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) > 500:
        raise ValueError("Maximum 500 records per portfolio request")
    return _backend("POST", "/v1/web-intelligence/portfolio", {"records": records})


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import JSONResponse

    try:
        backend = _backend("GET", "/health")
        return JSONResponse(
            {"status": "ok", "service": "multisport-edge-ai-mcp", "backend": backend}
        )
    except Exception as exc:
        return JSONResponse(
            {"status": "degraded", "service": "multisport-edge-ai-mcp", "error": str(exc)},
            status_code=503,
        )


security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    transport_security=security,
)
