import requests
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from ..config import settings

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
    params = {
        "api_key": api_key,
        "make": make,
        "model": model,
        "year": year,
        "rows": 50,  # Increased to 50 to maximize chance of finding one with a photo
        "photo_links": "true", # Explicitly request photo links
    }

    if trim:
        params["trim"] = trim
    
    if exterior_color:
        params["exterior_color"] = exterior_color
        
    if interior_color:
        params["interior_color"] = interior_color

    # Mileage range (e.g., +/- 10k miles if mileage is provided)
    if mileage:
        params["miles_range"] = f"{max(0, mileage - 10000)}-{mileage + 10000}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
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
                "image_url": primary_photo, # Add image URL to results
            })
        
        return {"results": results}

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except KeyError:
        return {"error": "Unexpected response format from API"}
