import requests
import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from ..config import settings

# Configure logging for this module
logger = logging.getLogger(__name__)

class MarketValuationInput(BaseModel):
    make: str = Field(..., description="The make of the vehicle.")
    model: str = Field(..., description="The model of the vehicle.")
    year: int = Field(..., description="The year of the vehicle.")
    trim: Optional[str] = Field(None, description="The trim level of the vehicle.")
    mileage: Optional[int] = Field(None, description="The mileage of the vehicle.")
    exterior_color: Optional[str] = Field(None, description="Exterior color.")
    interior_color: Optional[str] = Field(None, description="Interior color.")
    keywords: Optional[List[str]] = Field(None, description="Keywords to filter by.")

def search_market_listings(
    make: str, 
    model: str, 
    year: int, 
    trim: Optional[str] = None,
    mileage: Optional[int] = None,
    exterior_color: Optional[str] = None,
    interior_color: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Searches for market listings of similar vehicles using the Marketcheck API.
    """
    api_key = settings.marketcheck_api_key
    if not api_key:
        return {"error": "Marketcheck API key not configured."}

    url = "https://api.marketcheck.com/v2/search/car/active"
    
    # Base parameters (Relaxed Strategy)
    # We start with the most specific query, but if it fails, we might need to retry with fewer params.
    # For now, let's log exactly what we are sending.
    params = {
        "api_key": api_key,
        "year": str(year),
        "make": make,
        "model": model,
        "rows": "50",
        "start": "0",
        "stats": "price,miles",
        "photo_links": "true",
    }

    # Add optional specific parameters
    if trim:
        params["trim"] = trim
    
    if exterior_color:
        params["exterior_color"] = exterior_color
        
    if interior_color:
        params["interior_color"] = interior_color

    # Mileage range (e.g., +/- 10k miles if mileage is provided)
    if mileage:
        params["miles_range"] = f"{max(0, mileage - 10000)}-{mileage + 10000}"

    headers = {"Accept": "application/json"}

    # --- DEBUG LOGGING ---
    # Log the full request URL (masking API key for security)
    debug_params = params.copy()
    debug_params["api_key"] = "HIDDEN"
    print(f"DEBUG: Marketcheck Request -> URL: {url} | Params: {debug_params}")
    # ---------------------

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        num_found = data.get("num_found", 0)
        print(f"DEBUG: Marketcheck Response -> Found: {num_found} listings")

        # If no results found with specific params, try a fallback (Relaxed Search)
        if num_found == 0 and (exterior_color or interior_color or mileage):
            print("DEBUG: No results found. Retrying with relaxed parameters (Year/Make/Model/Trim)...")
            
            # Reset to base params + Trim (if available)
            relaxed_params = {
                "api_key": api_key,
                "year": str(year),
                "make": make,
                "model": model,
                "rows": "50",
                "start": "0",
                "stats": "price,miles",
                "photo_links": "true",
            }
            
            # Keep trim in the relaxed search if it was provided
            if trim:
                relaxed_params["trim"] = trim
            
            response = requests.get(url, headers=headers, params=relaxed_params)
            response.raise_for_status()
            data = response.json()
            print(f"DEBUG: Relaxed Search Response -> Found: {data.get('num_found', 0)} listings")

        results = []
        for listing in data.get("listings", []):
            # Extract image URL if available
            image_url = listing.get("media", {}).get("photo_links", [])
            primary_photo = image_url[0] if image_url else None

            results.append({
                "price": listing.get("price"),
                "miles": listing.get("miles"),
                "vin": listing.get("vin"),
                "trim": listing.get("trim"),
                "source": listing.get("source"),
                "exterior_color": listing.get("exterior_color"),
                "interior_color": listing.get("interior_color"),
                "seller_name": listing.get("dealer", {}).get("name"),
                "city": listing.get("dealer", {}).get("city"),
                "state": listing.get("dealer", {}).get("state"),
                "image_url": primary_photo,
            })
        
        return {"results": results}

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Marketcheck API Request Failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"ERROR RESPONSE: {e.response.text}")
        return {"error": f"API request failed: {e}"}
    except KeyError:
        return {"error": "Unexpected response format from API"}
