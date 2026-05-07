"""
Prompt renderer — thin Jinja2 wrapper for AI prompt templates.

Templates live in src/my_garage/prompts/ as .j2 files.
Each template receives a typed context dict from ContextService.to_dict().

Usage:
    from my_garage.utils.prompt_renderer import PromptRenderer

    renderer = PromptRenderer()
    prompt = renderer.render("vehicle_valuation.j2", context_dict)
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    UndefinedError,
)

logger = logging.getLogger(__name__)

# Default templates directory (relative to this file: ../../prompts/)
_DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptRenderError(Exception):
    """Raised when a template cannot be found or rendered."""


class PromptRenderer:
    """
    Renders Jinja2 prompt templates from the my_garage/prompts/ directory.

    StrictUndefined is used so missing context variables raise an error
    immediately rather than silently rendering as empty strings.
    """

    def __init__(self, template_dir: Path | str | None = None):
        template_dir = Path(template_dir) if template_dir else _DEFAULT_TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(self, template_name: str, context: dict) -> str:
        """
        Render a named template with the given context dict.

        Args:
            template_name: Filename of the template (e.g. "vehicle_valuation.j2").
            context: Dict of variables — typically from ContextService.to_dict().

        Returns:
            Rendered prompt string, stripped of leading/trailing whitespace.

        Raises:
            PromptRenderError: If template not found or a variable is missing.
        """
        try:
            template = self._env.get_template(template_name)
            return template.render(**context).strip()
        except TemplateNotFound as e:
            raise PromptRenderError(
                f"Prompt template not found: {template_name}. "
                f"Available templates: {self.list_templates()}"
            ) from e
        except UndefinedError as e:
            raise PromptRenderError(
                f"Missing context variable in template '{template_name}': {e}"
            ) from e

    def list_templates(self) -> list[str]:
        """Return all available template filenames."""
        return sorted(self._env.list_templates())

    def render_string(self, template_string: str, context: dict) -> str:
        """
        Render an ad-hoc template string (not a file).
        Useful for one-off prompts in tasks or views.
        """
        try:
            template = self._env.from_string(template_string)
            return template.render(**context).strip()
        except UndefinedError as e:
            raise PromptRenderError(f"Missing context variable: {e}") from e
