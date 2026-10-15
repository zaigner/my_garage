import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class CollectionThemeGenerator:
    """
    Uses Generative AI (Google Gemini via google-genai) to create rich,
    context-aware schemas and item descriptions for user collections.
    """

    def __init__(self):
        try:
            from google import genai

            # Ensure we have an API key
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning(
                    "No Google API key found. AI theme generation will be disabled."
                )
                self.enabled = False
            else:
                self.client = genai.Client(api_key=api_key)
                self.enabled = True
        except ImportError:
            logger.error("google-genai not installed. AI theme generation disabled.")
            self.enabled = False

    def generate_schema(
        self, collection_name: str, description: str = ""
    ) -> Dict[str, Any]:
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
            # Use gemini-2.5-flash
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            content = response.text
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

    def generate_item_description(self, item_context: dict) -> str:
        """Generate an auction-style curator's note for a collection item."""
        if not self.enabled:
            return ""

        try:
            from my_garage.utils.prompt_renderer import PromptRenderer

            renderer = PromptRenderer()
            prompt = renderer.render(
                "collection_item_description.j2", context=item_context
            )
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.error("Item description generation failed: %s", e)
            return ""

    def _get_fallback_schema(self, name: str) -> Dict[str, Any]:
        """Returns a safe default schema if AI fails."""
        return {
            "fields": [
                {
                    "name": "brand",
                    "type": "text",
                    "label": "Brand/Maker",
                    "required": True,
                    "help_text": "Who made this item?",
                },
                {
                    "name": "year",
                    "type": "number",
                    "label": "Year",
                    "required": False,
                    "help_text": "Year of production",
                },
                {
                    "name": "condition",
                    "type": "text",
                    "label": "Condition",
                    "required": False,
                    "help_text": "Current state of the item",
                },
                {
                    "name": "provenance",
                    "type": "text",
                    "label": "Provenance",
                    "required": False,
                    "help_text": "History of ownership",
                },
            ]
        }
