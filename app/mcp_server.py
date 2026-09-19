"""Retired anonymous bridge. Never forward private data or write requests."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health():
    return {"status": "ok", "service": "multisport-edge-ai-mcp", "anonymous_bridge": "disabled"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def retired(path: str):
    return JSONResponse(
        {"detail": "This anonymous bridge is retired. Connect the private OAuth report publisher.",
         "mcp_url": "https://multisport-edge-ai.onrender.com/mcp"},
        status_code=410, headers={"Cache-Control": "no-store"},
    )
