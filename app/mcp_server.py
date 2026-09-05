"""ChatGPT/MCP tool surface for MultiSport Edge AI.

This service deliberately does not call an LLM. ChatGPT supplies researched,
structured observations; the backend validates, scores, stores and optimizes them.
"""
from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.research_worker import prepare_batch
from app.web_pipeline import build_web_portfolio, qualify_records
from app.web_scan import ingest as ingest_web_records, snapshot as web_scan_snapshot

mcp = MCPServer(
    "multisport-edge-ai",
    title="MultiSport Edge AI",
    description=(
        "Research bridge for evidence-backed Betway and Sportingbet market observations. "
        "Use it to submit current research, inspect the >=90 analytical-confidence gate, "
        "and build a correlation-controlled 10-15 leg portfolio targeting 1.45-1.60."
    ),
    version="0.1.0",
    instructions=(
        "Never invent fixtures, odds, evidence or confidence. Research current public sources first. "
        "Submit only Betway or Sportingbet observations with source URLs and evidence. "
        "A >=90 analytical-confidence score is a qualification score, not a guaranteed win probability. "
        "If too few selections qualify, return NO_QUALIFIED_PORTFOLIO rather than forcing legs."
    ),
)


@mcp.tool(
    name="get_edge_status",
    description="Use this when you need the current MultiSport Edge scan and portfolio state.",
)
def get_edge_status() -> dict[str, Any]:
    """Return the current qualified-candidate and portfolio snapshot."""
    return web_scan_snapshot()


@mcp.tool(
    name="submit_research",
    description=(
        "Use this after researching current public sports sources to submit structured Betway or "
        "Sportingbet observations for backend validation and qualification."
    ),
)
def submit_research(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate research observations, ingest accepted records, and return the new scan."""
    if len(observations) > 500:
        raise ValueError("Maximum 500 observations per submission")
    prepared = prepare_batch(observations)
    ingestion = ingest_web_records(prepared["records"])
    return {
        "ok": True,
        "source": "chatgpt-mcp",
        "prepared": prepared,
        "ingestion": ingestion,
        "scan": web_scan_snapshot(),
    }


@mcp.tool(
    name="qualify_candidates",
    description="Use this to apply the backend qualification gate to supplied normalized records.",
)
def qualify_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the analytical-confidence and evidence qualification rules."""
    if len(records) > 500:
        raise ValueError("Maximum 500 records per qualification request")
    return qualify_records(records)


@mcp.tool(
    name="build_edge_portfolio",
    description=(
        "Use this after qualification to build the 10-15 leg correlation-controlled portfolio "
        "targeting combined odds 1.45-1.60."
    ),
)
def build_edge_portfolio(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a portfolio or explicitly return no qualified portfolio."""
    if len(records) > 500:
        raise ValueError("Maximum 500 records per portfolio request")
    return build_web_portfolio(records)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "service": "multisport-edge-ai-mcp"})


# Render terminates TLS and controls the public Host header. Disabling the SDK's
# localhost-only DNS-rebinding default is appropriate behind this managed proxy.
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    transport_security=security,
)
