"""
CollectionServiceRegistry — maps service_provider_key strings to provider instances.

Provider instances are module-level singletons (stateless objects).
Add new providers here as new collection specialisations are developed.

Usage:
    from my_garage.services.collection_services.registry import get_collection_services

    services = get_collection_services("vehicle")   # VehicleCollectionServices
    services = get_collection_services("unknown")   # DefaultCollectionServices (fallback)
"""
from __future__ import annotations

from .base import BaseCollectionServices
from .default import DefaultCollectionServices
from .timepiece import TimepieceCollectionServices
from .vehicle import VehicleCollectionServices

_DEFAULT = DefaultCollectionServices()

_REGISTRY: dict[str, BaseCollectionServices] = {
    "vehicle": VehicleCollectionServices(),
    "timepiece": TimepieceCollectionServices(),
    "default": _DEFAULT,
}


def get_collection_services(provider_key: str) -> BaseCollectionServices:
    """
    Return the service provider for *provider_key*.

    Falls back to DefaultCollectionServices for any unrecognised key so that
    generic user-created collections always have a safe, no-op provider.
    """
    return _REGISTRY.get(provider_key, _DEFAULT)


def register(key: str, provider: BaseCollectionServices) -> None:
    """
    Register a custom provider at runtime.  Intended for testing and for
    future plugin-style extensions.  Keys must be unique; existing entries
    are replaced.
    """
    _REGISTRY[key] = provider
