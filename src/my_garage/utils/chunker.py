"""
Text chunking utilities for the RAG knowledge index.

Strategy: split documents on markdown section headers (## or ###).
Each chunk includes the section header as context so retrieved
passages are self-contained and understandable without the parent doc.

Max tokens per chunk is approximated as max_chars / 4 (rough char-to-token ratio).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentChunk:
    content: str  # The text of this chunk
    source: str  # Filename or path this chunk came from
    section: str  # Nearest section header (empty string for preamble)
    chunk_index: int  # Position within the source document


def chunk_markdown(
    text: str, source: str, max_chars: int = 2000
) -> list[DocumentChunk]:
    """
    Split a markdown document into chunks by section (## / ### headers).

    Each chunk:
    - Includes the section header line so it's self-contained.
    - Is further split if it exceeds max_chars.
    - Strips leading/trailing whitespace.

    Args:
        text: Raw markdown content.
        source: Identifier for the source (filename used in metadata).
        max_chars: Maximum character length per chunk (default ~500 tokens).

    Returns:
        List of DocumentChunk objects.
    """
    if not text.strip():
        return []

    # Split on any line that starts with ## or ###
    header_pattern = re.compile(r"^(#{2,3}\s+.+)$", re.MULTILINE)
    parts = header_pattern.split(text)

    chunks: list[DocumentChunk] = []
    chunk_index = 0

    # parts alternates: [preamble, header, body, header, body, ...]
    # First element is the preamble (before first ## header)
    i = 0
    current_header = ""

    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue

        if header_pattern.match(parts[i]):
            current_header = parts[i].strip()
            i += 1
            continue

        # Combine header with body
        body = part
        full_content = f"{current_header}\n\n{body}".strip() if current_header else body

        # Further split if too long
        for sub_chunk in _split_on_length(full_content, max_chars):
            if sub_chunk.strip():
                chunks.append(
                    DocumentChunk(
                        content=sub_chunk.strip(),
                        source=source,
                        section=current_header,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1

        i += 1

    return chunks


def chunk_file(file_path: Path, max_chars: int = 2000) -> list[DocumentChunk]:
    """
    Read a markdown file and return its chunks.

    Args:
        file_path: Path to the .md file.
        max_chars: Maximum character length per chunk.
    """
    text = file_path.read_text(encoding="utf-8")
    return chunk_markdown(text, source=file_path.name, max_chars=max_chars)


def _split_on_length(text: str, max_chars: int) -> list[str]:
    """
    Split text that exceeds max_chars into smaller pieces at paragraph
    boundaries (double newlines). Falls back to hard splitting if no
    paragraph break is available.
    """
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    remaining = text

    while len(remaining) > max_chars:
        # Try to break at a paragraph boundary within the window
        window = remaining[:max_chars]
        split_pos = window.rfind("\n\n")

        if split_pos > max_chars // 2:
            parts.append(remaining[:split_pos].strip())
            remaining = remaining[split_pos:].strip()
        else:
            # No good paragraph break — split at a sentence boundary
            sentence_end = max(
                window.rfind(". "),
                window.rfind(".\n"),
            )
            if sentence_end > max_chars // 3:
                parts.append(remaining[: sentence_end + 1].strip())
                remaining = remaining[sentence_end + 1 :].strip()
            else:
                # Last resort: hard split
                parts.append(remaining[:max_chars].strip())
                remaining = remaining[max_chars:].strip()

    if remaining.strip():
        parts.append(remaining.strip())

    return parts
