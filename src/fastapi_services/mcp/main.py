from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from .tools import vehicle_lookup, market_valuation

router = APIRouter()

class MCPRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@router.post("/execute")
async def execute_mcp_tool(request: MCPRequest):
    """
    Endpoint for MCP tool execution.
    """
    print(f"Received MCP request: {request}")
    
    if request.tool_name == "search_market_listings":
        return market_valuation.search_market_listings(**request.arguments)
    
    elif request.tool_name == "lookup_vehicle_details":
        return vehicle_lookup.lookup_vehicle_details(**request.arguments)
        
    return {"error": "Tool not found"}
