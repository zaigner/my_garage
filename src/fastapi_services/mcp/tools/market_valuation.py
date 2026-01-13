import requests
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from ..config import settings

class MarketValuationInput(BaseModel):
    make: str = Field(..., description="The make of the vehicle.")
    model: str = Field(..., description="The model of the vehicle.")
    year: int = Field(..., description="The year of the vehicle.")

def search_market_listings(make: str, model: str, year: int) -> Dict[str, List[Dict[str, Any]]]:
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
        "rows": 10,  # Limit to 10 results for now
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        results = []
        for listing in data.get("listings", []):
            results.append({
                "price": listing.get("price"),
                "miles": listing.get("miles"),
                "vin": listing.get("vin"),
                "source": listing.get("source"),
                "exterior_color": listing.get("exterior_color"),
                "interior_color": listing.get("interior_color"),
                "seller_name": listing.get("dealer", {}).get("name"),
                "city": listing.get("dealer", {}).get("city"),
                "state": listing.get("dealer", {}).get("state"),
            })
        
        return {"results": results}

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except KeyError:
        return {"error": "Unexpected response format from API"}
