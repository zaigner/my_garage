import requests
import base64
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..config import settings

class ImageGenerationInput(BaseModel):
    prompt: str = Field(..., description="The prompt to generate an image from.")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt to avoid specific features.")

def generate_vehicle_image(prompt: str, negative_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates an image of a vehicle using Google Gemini 2.5 Flash Image (aka Nano Banana).
    """
    # Ensure you have GOOGLE_API_KEY in your .env and settings
    api_key = getattr(settings, "google_api_key", None) or getattr(settings, "gemini_api_key", None)

    if not api_key:
        return {"error": "Google API key not configured."}

    # Gemini 2.5 Flash Image (Nano Banana) Endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"

    # Construct the prompt with negative constraints if provided
    final_prompt = prompt
    if negative_prompt:
        final_prompt += f" --without {negative_prompt}"

    payload = {
        "contents": [{
            "parts": [{"text": final_prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "image/jpeg"
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract base64 image from Gemini response
        # Structure: candidates[0].content.parts[0].inlineData.data
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    return {"image_base64": part["inlineData"]["data"]}

        return {"error": "No image data found in Gemini response", "raw_response": data}

    except requests.exceptions.RequestException as e:
        return {"error": f"Google API request failed: {e}"}
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}
