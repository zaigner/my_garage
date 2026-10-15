"""
Scrub secrets out of text before it is logged or returned to a caller.

Marketcheck takes its API key as a query parameter, so a requests exception
for a failed call embeds the full URL — key included — in str(exc).
"""

from __future__ import annotations

REDACTED = "***"


def redact(text: str, secret: str | None) -> str:
    """Return text with every occurrence of secret replaced by REDACTED."""
    if not secret:
        return text
    return text.replace(secret, REDACTED)
