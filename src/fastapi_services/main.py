from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

class MCPRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@app.post("/mcp/execute")
async def execute_mcp_tool(request: MCPRequest):
    """
    Mock endpoint for MCP tool execution.
    In a real implementation, this would call the actual MCP agent.
    """
    print(f"Received MCP request: {request}")
    
    if request.tool_name == "search_market_listings":
        # Mock response for market valuation
        return {
            "results": [
                {"price": 45000, "source": "Bring a Trailer"},
                {"price": 42000, "source": "Cars & Bids"},
                {"price": 48000, "source": "eBay Motors"}
            ]
        }
    
    elif request.tool_name == "lookup_vehicle_details":
        # Mock response for vehicle enrichment
        return {
            "features": {
                "Transmission": "Manual",
                "Interior": "Leather",
                "Sunroof": "Panoramic"
            },
            "specs": {
                "Engine": "3.0L Inline-6",
                "Horsepower": "335 hp",
                "Torque": "365 lb-ft"
            },
            "photo_url": "https://example.com/car-photo.jpg"
        }
        
    return {"error": "Tool not found"}

@app.post("/ocr/process")
async def process_ocr(file: UploadFile = File(...)):
    """
    Mock endpoint for OCR processing.
    """
    return {
        "vendor": "AutoZone",
        "date": "2024-01-15",
        "total_cost": 125.50,
        "description": "Oil change and filter replacement",
        "line_items": [
            {"item": "Oil Filter", "price": 15.00},
            {"item": "Synthetic Oil 5qt", "price": 45.00}
        ]
    }
