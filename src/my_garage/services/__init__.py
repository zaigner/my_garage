"""
my_garage services package.

Context engineering layer — assembles structured, typed context
for AI interactions from the underlying Django ORM and MongoDB.
"""
from .context_service import ContextService

__all__ = ["ContextService"]
