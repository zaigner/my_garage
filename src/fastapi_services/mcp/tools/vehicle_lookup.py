import requests
from pydantic import BaseModel, Field
from typing import Dict, Any

class VehicleLookupInput(BaseModel):
    vin: str = Field(..., description="The VIN of the vehicle to look up.")

def lookup_vehicle_details(vin: str) -> Dict[str, Any]:
    """
    Looks up vehicle details based on the VIN using the NHTSA vPIC API.
    """
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        
        # Extract relevant information from the response
        results = {item['Variable']: item['Value'] for item in data['Results'] if item['Value']}
        
        if not results:
            return {"error": "VIN not found"}
            
        return {
            "make": results.get("Make"),
            "model": results.get("Model"),
            "year": results.get("Model Year"),
            "engine_cylinders": results.get("Engine Number of Cylinders"),
            "fuel_type": results.get("Fuel Type - Primary"),
            "transmission_style": results.get("Transmission Style"),
            "drivetrain": results.get("Drive Type"),
            "body_class": results.get("Body Class"),
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except KeyError:
        return {"error": "Unexpected response format from API"}
