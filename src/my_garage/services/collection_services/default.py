"""
DefaultCollectionServices — no-op provider for generic user-created collections.

All capability guards return False.  No external API calls are made.
This is the fallback returned by the registry for any unknown provider key.
"""

from __future__ import annotations

from .base import BaseCollectionServices


class DefaultCollectionServices(BaseCollectionServices):
    """
    Safe no-op provider used for every collection that has no registered
    specialisation (wine, sneakers, art, etc.).

    All supports_*() methods return False, so views and tasks will skip
    enrichment/valuation buttons and operations without error.
    """

    # All capability guards inherit the False defaults from BaseCollectionServices.
    # No run_* overrides needed — callers must check supports_*() first.
