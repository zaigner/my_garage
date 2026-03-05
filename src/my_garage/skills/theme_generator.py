import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CollectionThemeGenerator:
    """
    Uses Generative AI (Google Gemini via LiteLLM) to create rich,
    context-aware schemas and UI components for user collections.
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

    def generate_ui_component(self, collection_name: str, description: str = "", feedback: str = "") -> str:
        """
        Generates a custom Tailwind/Alpine.js UI component for the collection.
        Returns raw HTML string.
        """
        if not self.enabled:
            return "<!-- AI UI Generator disabled or unavailable -->"

        feedback_context = ""
        if feedback:
            feedback_context = f"""
            USER FEEDBACK ON PREVIOUS ITERATION:
            "{feedback}"
            
            ADJUSTMENT INSTRUCTION:
            Modify the design to specifically address the user's feedback above while maintaining all other requirements.
            """

        prompt = f"""You are an award-winning Digital Scenographer and UI Designer. Your goal is to create a visually immersive, thematic "digital home" for a specific collection.

TARGET COLLECTION: "{collection_name}"
CONTEXT: {description}
{feedback_context}

OBJECTIVE:
Create a highly atmospheric interface that captures the "vibe" of {collection_name} while maintaining functional parity with the default theme.
- If it's "Wine": Think dark cellars, deep reds/purples, serif fonts, gold accents, wood textures.
- If it's "Sneakers": Think streetwear, concrete/industrial backgrounds, bold sans-serifs, neon pops, high contrast.
- If it's "Coins/Stamps": Think museum display cases, velvet backgrounds (deep blue/green), spotlight effects.
- If it's "Comics": Think pop-art colors, dynamic borders, comic-book fonts.

TECH STACK:
1. HTML5 (Semantic)
2. Tailwind CSS (Use arbitrary values like bg-[#1a2b3c] freely to achieve specific colors).
3. Alpine.js (for interactivity).
4. Django Template Tags (REQUIRED).

CRITICAL REQUIREMENTS:
1. **Inheritance**: The output MUST NOT include `<html>`, `<head>`, or `<body>` tags. It will be injected into a template that extends `my_garage/base.html`. Start with a root `<div>` that has `min-h-screen` and your thematic background.
2. **Feature Parity**: You MUST include all the buttons and features found in the default theme:
   - **Header**: Title, Description, Stats (Total Items, Total Value).
   - **Action Bar**: "Add Item" button (Primary), "Edit Collection" button (Secondary).
   - **Search/Filter**: A search bar (can be visual only or functional with Alpine).
   - **View Toggle**: Buttons to switch between Grid/List (optional but good).
   - **Item Cards**: Must show Name, Photo (handle missing photo), Value, and a few key fields.
   - **Item Actions**: Each card needs an "Edit/View" link.

FUNCTIONALITY (MUST INCLUDE):
1. **Navigation**:
   - "Back" link: `<a href="{{% url 'collections:collection_type_list' %}}" ...>...</a>`
   - "Add Item" button: `<a href="{{% url 'collections:collection_item_add' collection_type.slug %}}" ...>...</a>`
   - "Edit Collection" button: `<a href="{{% url 'collections:collection_type_edit' collection_type.slug %}}" ...>...</a>`
2. **Item Loop**:
   - **IMPORTANT**: Use EXACTLY this syntax for the loop: `{{% for item in items %}}` ... `{{% endfor %}}`
   - Link to Detail: `{{% url 'collections:collection_item_detail' collection_type.slug item.id %}}`
   - Image: `{{% if item.photo %}}<img src="{{{{ item.photo.url }}}}" ...>{{% else %}}...{{% endif %}}`
   - Data: `{{{{ item.name }}}}`, `{{{{ item.current_market_value }}}}`, `{{{{ item.purchase_price }}}}`.
3. **Empty State**: Handle `{{% empty %}}` gracefully with a thematic message and an "Add Item" button.

DESIGN RULES:
- **Typography**: You MAY include a `<link>` to Google Fonts at the top of the HTML to import a font that matches the theme perfectly. Apply it via `style="font-family: ..."` on the root container.
- **Background**: The root container MUST have `min-h-screen` and a thematic background (color, gradient, or pattern).
- **Cards**: Use glassmorphism (`bg-white/10 backdrop-blur-md`), borders, or shadows to make items pop against the background.
- **Responsiveness**: Must look great on mobile and desktop.

OUTPUT FORMAT:
- Return ONLY the raw HTML code inside a single ```html``` block.
- Do not include any explanations.
"""

        try:
            response = self.litellm.completion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
            )
            
            content = response.choices[0].message.content
            
            # Extract HTML from markdown block
            if "```html" in content:
                content = content.split("```html")[1].split("```")[0].strip()
            elif "```" in content:
                # This handles the case where the AI might output ```html ... ``` or just ``` ... ```
                parts = content.split("```")
                if len(parts) >= 3:
                    code_block = parts[1]
                    if code_block.strip().lower().startswith("html"):
                        content = code_block.strip()[4:].strip()
                    else:
                        content = code_block.strip()

            return content

        except Exception as e:
            logger.error(f"AI UI Generation failed: {e}")
            return f"<!-- Error generating UI: {str(e)} -->"

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
