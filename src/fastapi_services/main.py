from contextlib import asynccontextmanager

from fastapi import FastAPI

from .mcp import main as mcp_router
from .mcp.config import settings as mcp_settings
from .mcp.server import mcp_server
from .ocr import main as ocr_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log which tools are available based on configured API keys
    mcp_settings.log_startup_status()
    yield


app = FastAPI(
    title="My Garage AI Services",
    version="1.0.0",
    lifespan=lifespan,
)

# Legacy REST API — Django service layer calls POST /mcp/execute (unchanged)
app.include_router(mcp_router.router, prefix="/mcp", tags=["mcp-rest"])
app.include_router(ocr_router.router, prefix="/ocr", tags=["ocr"])

# Real MCP server — Claude Code connects here via HTTP (streamable-http) transport.
# Registered in .claude/settings.local.json as: "url": "http://localhost:8001/mcp-sdk"
app.mount("/mcp-sdk", mcp_server.streamable_http_app())
