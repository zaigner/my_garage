from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Field

from ..config import settings


class SalesStatsInput(BaseModel):
    year: int = Field(..., description="Vehicle year.")
    make: str = Field(..., description="Vehicle make.")
    model: str = Field(..., description="Vehicle model.")
    trim: Optional[str] = Field(
        None, description="Vehicle trim level for more precision."
    )
    zip_code: Optional[str] = Field(
        None, description="Zip code for local market analysis."
    )
    radius: Optional[int] = Field(
        None, description="Search radius in miles (default 500)."
    )


class SalesHistoryInput(BaseModel):
    vin: str = Field(..., description="Vehicle VIN.")


def get_sales_stats(
    year: int,
    make: str,
    model: str,
    trim: Optional[str] = None,
    zip_code: Optional[str] = None,
    radius: Optional[int] = 500,
) -> Dict[str, Any]:
    """
    Retrieves inferred sales statistics (sold data) from Marketcheck.
    Useful for determining the 'real' market value of a vehicle based on sales history.
    """
    api_key = settings.marketcheck_api_key
    if not api_key:
        return {"error": "Marketcheck API key not configured."}

    # Endpoint for sales statistics
    url = "https://api.marketcheck.com/v2/stats/sales"

    # Construct parameters
    params = {
        "api_key": api_key,
        "year": year,
        "make": make,
        "model": model,
        "car_type": "used",
        "country": "US",
    }

    if trim:
        params["trim"] = trim

    if zip_code:
        params["zip"] = zip_code
        params["radius"] = radius or 500

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data

    except requests.exceptions.RequestException as e:
        return {"error": f"Marketcheck API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Sales stats lookup failed: {str(e)}"}


def get_sales_history_by_vin(vin: str) -> Dict[str, Any]:
    """
    Retrieves sales history for a specific vehicle by VIN from Marketcheck.
    This endpoint returns comparable sales or history for the specific VIN if available.
    """
    api_key = settings.marketcheck_api_key
    if not api_key:
        return {"error": "Marketcheck API key not configured."}

    url = "https://api.marketcheck.com/v2/sales/car"

    params = {
        "api_key": api_key,
        "vin": vin,
        "car_type": "used",
    }

    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"Marketcheck API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Sales history lookup failed: {str(e)}"}
