"""
Management command: build_knowledge_index

Scans project .md files, chunks them by section, embeds each chunk
using the Google text-embedding-004 model, and upserts into MongoDB.

Retrieval uses Python cosine similarity (compatible with local MongoDB 6.x).
No Atlas Vector Search index is required.

Usage:
    pixi run manage build_knowledge_index
    pixi run manage build_knowledge_index --source-dir docs
    pixi run manage build_knowledge_index --dry-run
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from my_garage.utils.chunker import DocumentChunk, chunk_file
from my_garage.utils.mongo import get_collection

logger = logging.getLogger(__name__)

# Markdown files to index relative to BASE_DIR.
# Add new knowledge files here as the project grows.
DEFAULT_SOURCE_FILES = [
    "SERVICE_RECORDS_GUIDE.md",
    "UPGRADES_KANBAN_GUIDE.md",
    "DYNAMIC_COLLECTIONS_GUIDE.md",
    "claude.md",
    ".specify/specs/001-my-garage-platform/spec.md",
    ".specify/memory/constitution.md",
]

EMBEDDING_MODEL = "gemini-embedding-001"
MONGO_COLLECTION = "knowledge_chunks"
VECTOR_INDEX_NAME = "knowledge_embedding_index"


class Command(BaseCommand):
    help = (
        "Build or refresh the RAG knowledge index in MongoDB. "
        "Chunks all project .md files and embeds them using Google text-embedding-004."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chunk files and count results without writing to MongoDB.",
        )
        parser.add_argument(
            "--source-dir",
            type=str,
            default=None,
            help="Index all .md files in this directory (relative to BASE_DIR).",
        )
        parser.add_argument(
            "--max-chars",
            type=int,
            default=2000,
            help="Maximum characters per chunk (default 2000 ≈ 500 tokens).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        source_dir: str | None = options["source_dir"]
        max_chars: int = options["max_chars"]

        base_dir = Path(settings.BASE_DIR)

        # Collect files to index
        files: list[Path] = []
        if source_dir:
            target_dir = base_dir / source_dir
            if not target_dir.is_dir():
                raise CommandError(f"Source directory not found: {target_dir}")
            files = list(target_dir.rglob("*.md"))
            self.stdout.write(f"Found {len(files)} .md files in {target_dir}")
        else:
            for rel_path in DEFAULT_SOURCE_FILES:
                full_path = base_dir / rel_path
                if full_path.exists():
                    files.append(full_path)
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  Skipping (not found): {rel_path}")
                    )

        if not files:
            self.stdout.write(self.style.WARNING("No files to index."))
            return

        # Chunk all files
        all_chunks: list[DocumentChunk] = []
        for file_path in files:
            chunks = chunk_file(file_path, max_chars=max_chars)
            self.stdout.write(f"  {file_path.name}: {len(chunks)} chunks")
            all_chunks.extend(chunks)

        self.stdout.write(self.style.SUCCESS(f"\nTotal chunks: {len(all_chunks)}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes written."))
            return

        # Embed and upsert
        api_key = getattr(settings, "GOOGLE_API_KEY", None)
        if not api_key:
            raise CommandError(
                "GOOGLE_API_KEY is not set. "
                "Add it to your .env file to enable embeddings."
            )

        collection = get_collection(MONGO_COLLECTION)
        embedded = 0
        skipped = 0

        for chunk in all_chunks:
            embedding = self._embed(chunk.content, api_key)
            if embedding is None:
                skipped += 1
                continue

            # Upsert: key on (source, chunk_index)
            collection.update_one(
                {"source": chunk.source, "chunk_index": chunk.chunk_index},
                {
                    "$set": {
                        "content": chunk.content,
                        "source": chunk.source,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                        "embedding": embedding,
                    }
                },
                upsert=True,
            )
            embedded += 1

            if embedded % 10 == 0:
                self.stdout.write(f"  Embedded {embedded}/{len(all_chunks)}...")

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. Embedded: {embedded}, Skipped: {skipped}")
        )
        self.stdout.write(
            "Retrieval uses Python cosine similarity — no vector index required."
        )

    def _embed(self, text: str, api_key: str) -> list[float] | None:
        """Embed a single text chunk via the Google API. Returns None on error."""
        try:
            from google import genai as google_genai

            client = google_genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.warning(f"Embedding failed for chunk: {e}")
            return None
