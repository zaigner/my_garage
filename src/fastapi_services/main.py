from fastapi import FastAPI
from .mcp import main as mcp_router
from .ocr import main as ocr_router

app = FastAPI()

app.include_router(mcp_router.router, prefix="/mcp", tags=["mcp"])
app.include_router(ocr_router.router, prefix="/ocr", tags=["ocr"])
