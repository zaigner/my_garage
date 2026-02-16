import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CollectionThemeGenerator:
    """
    Uses Generative AI (Google Gemini via LiteLLM) to create rich,
    context-aware schemas for user collections.
    """
    
    def __init__(self):
        # We'll use litellm to abstract the provider
        try:
            import litellm
            self.litellm = litellm
            # Ensure we have an API key
            if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
                logger.warning("No Google API key found. AI theme generation will be disabled.")
                self.enabled = False
            else:
                self.enabled = True
        except ImportError:
            logger.error("LiteLLM not installed. AI theme generation disabled.")
            self.enabled = False

    def generate_schema(self, collection_name: str, description: str = "") -> Dict[str, Any]:
        """
        Generates a JSON schema for a collection type based on its name and description.
        Returns a dictionary compatible with CollectionType.field_schema.
        """
        if not self.enabled:
            logger.warning("AI Theme Generator is disabled. Returning fallback schema.")
            return self._get_fallback_schema(collection_name)

        prompt = f"""
        You are an expert archivist and database architect for a high-end asset management platform.
        
        Task: Create a data schema for a collection of: "{collection_name}"
        Context: {description}
        
        The schema must be a JSON object with a 'fields' list. Each field must have:
        - name: snake_case identifier
        - type: one of ['text', 'number', 'date', 'file', 'relationship']
        - label: Human readable label
        - required: boolean
        - help_text: Short description
        
        Include 5-8 specific fields that an expert collector would track.
        Do NOT include standard fields like 'name', 'photo', 'purchase_price', 'value', 'notes' as these are built-in.
        
        Example for 'Wine':
        {{
            "fields": [
                {{"name": "vintage", "type": "number", "label": "Vintage", "required": true, "help_text": "Year of production"}},
                {{"name": "producer", "type": "text", "label": "Producer", "required": true, "help_text": "Winery or estate"}},
                {{"name": "varietal", "type": "text", "label": "Varietal", "required": true, "help_text": "Grape type"}},
                {{"name": "region", "type": "text", "label": "Region", "required": false, "help_text": "Geographic origin"}},
                {{"name": "drink_window_start", "type": "number", "label": "Drink From", "required": false, "help_text": "Year ready to drink"}},
                {{"name": "drink_window_end", "type": "number", "label": "Drink Until", "required": false, "help_text": "Year past peak"}}
            ]
        }}
        
        Return ONLY the JSON object.
        """

        try:
            # Use gemini-2.5-flash as requested (or latest stable)
            # Note: Model names change frequently. 'gemini/gemini-2.0-flash' is a good target for latest.
            response = self.litellm.completion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
            )
            
            content = response.choices[0].message.content
            # Clean up potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            schema = json.loads(content)
            
            # Basic validation
            if "fields" not in schema:
                logger.error("AI returned invalid schema structure")
                return self._get_fallback_schema(collection_name)
                
            return schema
            
        except Exception as e:
            logger.error(f"AI Schema Generation failed: {e}")
            return self._get_fallback_schema(collection_name)

    def _get_fallback_schema(self, name: str) -> Dict[str, Any]:
        """Returns a safe default schema if AI fails."""
        return {
            "fields": [
                {
                    "name": "brand",
                    "type": "text",
                    "label": "Brand/Maker",
                    "required": True,
                    "help_text": "Who made this item?"
                },
                {
                    "name": "year",
                    "type": "number",
                    "label": "Year",
                    "required": False,
                    "help_text": "Year of production"
                },
                {
                    "name": "condition",
                    "type": "text",
                    "label": "Condition",
                    "required": False,
                    "help_text": "Current state of the item"
                },
                {
                    "name": "provenance",
                    "type": "text",
                    "label": "Provenance",
                    "required": False,
                    "help_text": "History of ownership"
                }
            ]
        }
