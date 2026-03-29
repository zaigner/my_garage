"""
Pluggable service provider system for unified collections.

Usage:
    from my_garage.services.collection_services import get_collection_services

    services = get_collection_services(item.collection_type.service_provider_key)
    if services.supports_valuation_refresh():
        new_value = services.run_valuation(item)
"""

from .registry import get_collection_services

__all__ = ["get_collection_services"]
