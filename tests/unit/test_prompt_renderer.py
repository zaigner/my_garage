"""
Tests for the Jinja2 prompt renderer (Phase 2.1).
No Django DB or external services needed.
"""
from __future__ import annotations

import pytest

from my_garage.utils.prompt_renderer import PromptRenderer, PromptRenderError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer():
    """Renderer pointing at the real prompts directory."""
    return PromptRenderer()


@pytest.fixture
def tmp_renderer(tmp_path):
    """Renderer with a temporary template directory for isolation."""
    return PromptRenderer(template_dir=tmp_path), tmp_path


# ---------------------------------------------------------------------------
# Template listing
# ---------------------------------------------------------------------------


class TestListTemplates:
    def test_all_four_templates_present(self, renderer):
        templates = renderer.list_templates()
        expected = {
            "vehicle_valuation.j2",
            "service_record_analysis.j2",
            "condition_assessment.j2",
            "collection_item_description.j2",
        }
        assert expected.issubset(
            set(templates)
        ), f"Missing templates: {expected - set(templates)}"

    def test_returns_sorted_list(self, renderer):
        templates = renderer.list_templates()
        assert templates == sorted(templates)


# ---------------------------------------------------------------------------
# render (file-based templates)
# ---------------------------------------------------------------------------


class TestRender:
    def _vehicle_context(self, **overrides) -> dict:
        base = {
            "year": 2019,
            "make": "Porsche",
            "model": "911",
            "trim": "Carrera S",
            "vin": "WP0AB2A91KS123456",
            "exterior_color": "Guards Red",
            "interior_color": "Black",
            "transmission": "7-Speed PDK",
            "mileage": 12000,
            "purchase_price": "85000.00",
            "current_market_value": "92000.00",
            "total_maintenance_cost": "1200.00",
            "total_upgrade_cost": "500.00",
            "total_investment": "86700.00",
            "equity": "5300.00",
            "is_profitable": True,
            "service_records": [],
            "relevant_docs": [],
        }
        base.update(overrides)
        return base

    def test_vehicle_valuation_renders(self, renderer):
        ctx = self._vehicle_context()
        result = renderer.render("vehicle_valuation.j2", ctx)
        assert "Porsche" in result
        assert "911" in result
        assert "92000" in result

    def test_vehicle_valuation_includes_service_records(self, renderer):
        ctx = self._vehicle_context(
            service_records=[
                {
                    "date": "2023-01-15",
                    "vendor": "Porsche of Austin",
                    "category": "MAINTENANCE",
                    "total_cost": "1200.00",
                }
            ]
        )
        result = renderer.render("vehicle_valuation.j2", ctx)
        assert "Porsche of Austin" in result

    def test_vehicle_valuation_includes_relevant_docs(self, renderer):
        ctx = self._vehicle_context(
            relevant_docs=["Market context: Carrera S values are rising."]
        )
        result = renderer.render("vehicle_valuation.j2", ctx)
        assert "Market context" in result

    def test_service_record_analysis_renders(self, renderer):
        ctx = {
            "year": 2019,
            "make": "Porsche",
            "model": "911",
            "trim": "Carrera S",
            "mileage": 12000,
            "service_records": [
                {
                    "date": "2023-01-15",
                    "vendor": "Porsche of Austin",
                    "category": "MAINTENANCE",
                    "total_cost": "1200.00",
                    "description": "Annual service",
                    "is_verified": True,
                }
            ],
            "relevant_docs": [],
        }
        result = renderer.render("service_record_analysis.j2", ctx)
        assert "Annual service" in result

    def test_collection_item_description_renders(self, renderer):
        ctx = {
            "name": "2015 Opus One",
            "collection_type_name": "Wine Collection",
            "purchase_price": "350.00",
            "purchase_date": "2020-03-15",
            "current_market_value": "420.00",
            "custom_fields": {"vintage": 2015, "region": "Napa Valley"},
            "notes": "Excellent condition.",
            "service_record_count": 0,
            "relevant_docs": [],
        }
        result = renderer.render("collection_item_description.j2", ctx)
        assert "Opus One" in result
        assert "Wine" in result

    def test_raises_on_missing_template(self, renderer):
        with pytest.raises(PromptRenderError, match="not found"):
            renderer.render("nonexistent_template.j2", {})

    def test_raises_on_missing_context_variable(self, renderer):
        # vehicle_valuation.j2 requires 'make' — omit it
        ctx = self._vehicle_context()
        del ctx["make"]
        with pytest.raises(PromptRenderError, match="Missing context variable"):
            renderer.render("vehicle_valuation.j2", ctx)


# ---------------------------------------------------------------------------
# render_string
# ---------------------------------------------------------------------------


class TestRenderString:
    def test_renders_simple_string(self):
        renderer = PromptRenderer()
        result = renderer.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_raises_on_missing_variable(self):
        renderer = PromptRenderer()
        with pytest.raises(PromptRenderError, match="Missing context variable"):
            renderer.render_string("Hello {{ name }}!", {})

    def test_renders_conditionals(self):
        renderer = PromptRenderer()
        tmpl = "{% if show %}visible{% else %}hidden{% endif %}"
        assert renderer.render_string(tmpl, {"show": True}) == "visible"
        assert renderer.render_string(tmpl, {"show": False}) == "hidden"


# ---------------------------------------------------------------------------
# Custom template directory
# ---------------------------------------------------------------------------


class TestCustomTemplateDir:
    def test_uses_custom_directory(self, tmp_renderer):
        renderer, tmp_path = tmp_renderer
        (tmp_path / "greeting.j2").write_text("Hello {{ name }}!")
        result = renderer.render("greeting.j2", {"name": "Claude"})
        assert result == "Hello Claude!"

    def test_lists_templates_in_custom_dir(self, tmp_renderer):
        renderer, tmp_path = tmp_renderer
        (tmp_path / "a.j2").write_text("A")
        (tmp_path / "b.j2").write_text("B")
        assert set(renderer.list_templates()) == {"a.j2", "b.j2"}
