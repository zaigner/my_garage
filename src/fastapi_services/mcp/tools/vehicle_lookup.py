import requests
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class VehicleLookupInput(BaseModel):
    vin: str = Field(..., description="The VIN of the vehicle to look up.")
    model_year: Optional[int] = Field(None, description="The model year of the vehicle for a more accurate lookup.")

def lookup_vehicle_details(vin: str, model_year: Optional[int] = None) -> Dict[str, Any]:
    """
    Looks up vehicle details based on the VIN using the NHTSA vPIC API.
    Includes the model year for a more accurate decoding and filters out metadata.
    """
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
    if model_year:
        url += f"&modelyear={model_year}"
    
    # A set of keys to ignore from the API response as they are not vehicle specs.
    IGNORED_KEYS = {
        'error_code',
        'error_text',
        'additional_error_text',
        'possible_values',
        'suggested_vin',
    }
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        results = {
            item['Variable'].replace(' ', '_').lower(): item['Value'] 
            for item in data['Results'] 
            if item['Value']
        }
        
        if not results:
            return {"error": "VIN not found"}

        # Filter out the ignored keys to return only clean spec data
        clean_results = {k: v for k, v in results.items() if k not in IGNORED_KEYS}
            
        return clean_results

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except KeyError:
        return {"error": "Unexpected response format from API"}
