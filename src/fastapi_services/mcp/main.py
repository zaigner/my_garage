from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import tools
from .tools import (
    google_search,
    image_generation,
    market_valuation,
    sales_stats,
    vehicle_lookup,
    watch_valuation,
)

router = APIRouter()


class MCPRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


@router.post("/execute")
async def execute_mcp_tool(request: MCPRequest):
    """
    Executes a specific MCP tool based on the request.
    """
    try:
        if request.tool_name == "lookup_vehicle_details":
            # Validate arguments using Pydantic model
            # In a real MCP server, this would be dynamic
            return vehicle_lookup.lookup_vehicle_details(**request.arguments)

        elif request.tool_name == "search_market_listings":
            return market_valuation.search_market_listings(**request.arguments)

        elif request.tool_name == "search_google_images":
            return google_search.search_google_images(**request.arguments)

        elif request.tool_name == "generate_vehicle_image":
            return image_generation.generate_vehicle_image(**request.arguments)

        elif request.tool_name == "get_sales_stats":
            return sales_stats.get_sales_stats(**request.arguments)

        elif request.tool_name == "get_sales_history_by_vin":
            return sales_stats.get_sales_history_by_vin(**request.arguments)

        elif request.tool_name == "get_watch_valuation":
            return watch_valuation.get_watch_valuation(**request.arguments)

        else:
            raise HTTPException(
                status_code=404, detail=f"Tool '{request.tool_name}' not found."
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
