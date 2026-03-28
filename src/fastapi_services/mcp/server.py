"""
Real MCP server using the official MCP Python SDK (mcp>=1.0).
Claude Code connects to this via HTTP (streamable-http) transport at /mcp-sdk/.

The existing REST router at /mcp/execute is preserved for the Django service layer.
These are two separate interfaces:
  - /mcp/execute  → Django calls this programmatically (REST)
  - /mcp-sdk/     → Claude Code uses this natively (MCP protocol)
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .tools import (
    google_search,
    image_generation,
    market_valuation,
    sales_stats,
    vehicle_lookup,
    watch_valuation,
)

mcp_server = FastMCP(
    "my-garage",
    instructions=(
        "My Garage asset management tools. "
        "Provides vehicle VIN lookup, market valuations, sales history, "
        "watch valuations, image generation, and image search."
    ),
)


@mcp_server.tool()
def lookup_vehicle_details(vin: str, model_year: Optional[int] = None) -> dict:
    """
    Look up vehicle details using the NHTSA vPIC API (free, no key required).
    Returns make, model, year, engine, body style, and all decoded spec data for the given VIN.

    Args:
        vin: The 17-character Vehicle Identification Number.
        model_year: Optional model year for more accurate decoding.
    """
    return vehicle_lookup.lookup_vehicle_details(vin, model_year)


@mcp_server.tool()
def search_market_listings(
    make: str,
    model: str,
    year: int,
    trim: Optional[str] = None,
    mileage: Optional[int] = None,
    exterior_color: Optional[str] = None,
    interior_color: Optional[str] = None,
) -> dict:
    """
    Search active vehicle market listings via Marketcheck API.
    Returns price, mileage, trim, dealer info, and photo URLs for comparable vehicles.
    Falls back to a relaxed search (make/model/year only) if no results found.

    Args:
        make: Vehicle manufacturer (e.g. "Porsche", "Toyota").
        model: Vehicle model (e.g. "911", "Supra").
        year: Model year as integer.
        trim: Trim level for more precise matching (e.g. "Carrera S").
        mileage: Current mileage for comparable-mileage search.
        exterior_color: Exterior paint color name.
        interior_color: Interior color name.
    """
    return market_valuation.search_market_listings(
        make=make,
        model=model,
        year=year,
        trim=trim,
        mileage=mileage,
        exterior_color=exterior_color,
        interior_color=interior_color,
    )


@mcp_server.tool()
def get_sales_stats(
    year: int,
    make: str,
    model: str,
    trim: Optional[str] = None,
    zip_code: Optional[str] = None,
    radius: Optional[int] = 500,
) -> dict:
    """
    Get inferred sales statistics (sold/transacted data) from Marketcheck.
    Useful for determining real market value based on actual completed sales.

    Args:
        year: Model year.
        make: Vehicle manufacturer.
        model: Vehicle model.
        trim: Trim level for precision.
        zip_code: ZIP code for local market analysis.
        radius: Search radius in miles (default 500).
    """
    return sales_stats.get_sales_stats(
        year=year,
        make=make,
        model=model,
        trim=trim,
        zip_code=zip_code,
        radius=radius,
    )


@mcp_server.tool()
def get_sales_history_by_vin(vin: str) -> dict:
    """
    Get the complete sales history for a specific vehicle by VIN from Marketcheck.
    Shows how many times it has sold and at what prices.

    Args:
        vin: The 17-character Vehicle Identification Number.
    """
    return sales_stats.get_sales_history_by_vin(vin=vin)


@mcp_server.tool()
def get_watch_valuation(
    brand: str,
    model: str,
    reference_number: Optional[str] = None,
    year: Optional[int] = None,
    condition_grade: Optional[str] = None,
    has_box: bool = False,
    has_papers: bool = False,
) -> dict:
    """
    Get an estimated market valuation for a timepiece/watch.
    Factors in brand prestige, model, reference number, condition, and completeness.

    Args:
        brand: Watch manufacturer (e.g. "Rolex", "Patek Philippe").
        model: Watch model name (e.g. "Submariner", "Nautilus").
        reference_number: Reference number for precise identification (e.g. "5711/1A").
        year: Year of manufacture.
        condition_grade: Condition description (e.g. "Mint", "Good", "Unworn").
        has_box: Whether the original box is present.
        has_papers: Whether the original papers/certificate are present.
    """
    return watch_valuation.get_watch_valuation(
        brand=brand,
        model=model,
        reference_number=reference_number,
        year=year,
        condition_grade=condition_grade,
        has_box=has_box,
        has_papers=has_papers,
    )


@mcp_server.tool()
def generate_vehicle_image(prompt: str, negative_prompt: Optional[str] = None) -> dict:
    """
    Generate a photorealistic vehicle image using Google Gemini.
    Returns a base64-encoded JPEG image suitable for saving as a vehicle photo.

    Args:
        prompt: Detailed description of the desired image
                (e.g. "2019 Porsche 911 Carrera S in Guards Red, studio lighting").
        negative_prompt: Features to avoid in the generated image.
    """
    return image_generation.generate_vehicle_image(
        prompt=prompt, negative_prompt=negative_prompt
    )


@mcp_server.tool()
def search_google_images(query: str) -> dict:
    """
    Search Google Images and return a list of image URLs for the given query.
    Useful for finding reference photos of vehicles or timepieces.

    Args:
        query: Search terms (e.g. "2019 Porsche 911 GT3 RS Guards Red").
    """
    return google_search.search_google_images(query=query)
