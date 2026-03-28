"""
Tests for the text chunker (Phase 1.2).
No Django DB or external services needed.
"""
from __future__ import annotations

from my_garage.utils.chunker import DocumentChunk, _split_on_length, chunk_markdown

# ---------------------------------------------------------------------------
# chunk_markdown
# ---------------------------------------------------------------------------


class TestChunkMarkdown:
    def test_empty_text_returns_empty_list(self):
        assert chunk_markdown("", source="test.md") == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_markdown("   \n\n  ", source="test.md") == []

    def test_single_section_returns_one_chunk(self):
        text = "## Overview\n\nThis is the intro paragraph."
        chunks = chunk_markdown(text, source="doc.md")
        assert len(chunks) == 1
        assert "Overview" in chunks[0].content
        assert "intro paragraph" in chunks[0].content

    def test_multiple_sections_returns_multiple_chunks(self):
        text = (
            "## Section A\n\nContent of A.\n\n"
            "## Section B\n\nContent of B.\n\n"
            "## Section C\n\nContent of C."
        )
        chunks = chunk_markdown(text, source="doc.md")
        assert len(chunks) == 3

    def test_source_is_set_on_all_chunks(self):
        text = "## A\n\nFoo.\n\n## B\n\nBar."
        chunks = chunk_markdown(text, source="guide.md")
        assert all(c.source == "guide.md" for c in chunks)

    def test_chunk_index_is_sequential(self):
        text = "## A\n\nFoo.\n\n## B\n\nBar.\n\n## C\n\nBaz."
        chunks = chunk_markdown(text, source="doc.md")
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_section_header_is_captured(self):
        text = "## Service Records\n\nTrack your maintenance here."
        chunks = chunk_markdown(text, source="doc.md")
        assert chunks[0].section == "## Service Records"

    def test_preamble_before_first_header_is_chunked(self):
        text = "This is preamble text.\n\n## First Section\n\nContent."
        chunks = chunk_markdown(text, source="doc.md")
        # Preamble + section = at least 2 chunks (or 1 if preamble is small)
        assert len(chunks) >= 1
        content_combined = " ".join(c.content for c in chunks)
        assert "preamble" in content_combined
        assert "Content" in content_combined

    def test_long_section_is_split(self):
        # Create a section with content longer than max_chars
        long_body = "Word " * 600  # ~3000 chars
        text = f"## Long Section\n\n{long_body}"
        chunks = chunk_markdown(text, source="doc.md", max_chars=500)
        assert len(chunks) > 1

    def test_returns_document_chunk_instances(self):
        text = "## Test\n\nSome content."
        chunks = chunk_markdown(text, source="doc.md")
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_chunks_are_stripped(self):
        text = "## Section\n\n   Content with spaces.   "
        chunks = chunk_markdown(text, source="doc.md")
        assert chunks[0].content == chunks[0].content.strip()

    def test_h3_headers_also_split(self):
        text = "### Sub-section A\n\nDetail A.\n\n" "### Sub-section B\n\nDetail B."
        chunks = chunk_markdown(text, source="doc.md")
        assert len(chunks) == 2


# ---------------------------------------------------------------------------
# _split_on_length
# ---------------------------------------------------------------------------


class TestSplitOnLength:
    def test_short_text_not_split(self):
        text = "Short text."
        result = _split_on_length(text, max_chars=1000)
        assert result == ["Short text."]

    def test_long_text_split_at_paragraph(self):
        para1 = "First paragraph. " * 30
        para2 = "Second paragraph. " * 30
        text = para1 + "\n\n" + para2
        result = _split_on_length(text, max_chars=len(para1) + 10)
        assert len(result) >= 2

    def test_all_parts_non_empty(self):
        text = "A" * 3000
        result = _split_on_length(text, max_chars=500)
        assert all(part.strip() for part in result)

    def test_total_content_preserved(self):
        text = "Hello world. " * 200
        result = _split_on_length(text, max_chars=300)
        combined = " ".join(result).replace("  ", " ")
        # Content should be preserved (whitespace normalization may differ)
        assert len(combined) >= len(text) * 0.9
