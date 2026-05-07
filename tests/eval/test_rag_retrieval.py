"""
Eval tests: RAG retrieval (Phase 3.2).
Tests that the ContextService.retrieve_relevant_docs() behaves correctly
under mocked MongoDB and embedding conditions.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


class TestRagRetrievalGoldenDataset:
    def test_returns_list_type(self, golden_dataset, context_service):
        case = next(c for c in golden_dataset if c["id"] == "rag_returns_list")

        with patch.object(context_service, "_embed_query", return_value=None):
            result = context_service.retrieve_relevant_docs(case["query"])

        assert isinstance(result, list), f"Expected list, got {type(result)}"

    def test_empty_query_returns_empty_list(self, golden_dataset, context_service):
        case = next(c for c in golden_dataset if c["id"] == "rag_empty_query")
        result = context_service.retrieve_relevant_docs(case["query"])
        assert result == case["expected_result"]

    def test_returns_content_strings(self, context_service):
        """When MongoDB has data, retrieved items must be strings."""
        mock_embedding = [1.0] + [0.0] * 767
        mock_chunks = [
            {
                "content": "Service records track maintenance history.",
                "embedding": [1.0] + [0.0] * 767,
            },
            {
                "content": "Use the Kanban board for upgrades.",
                "embedding": [0.0] + [1.0] + [0.0] * 766,
            },
        ]
        with patch.object(context_service, "_embed_query", return_value=mock_embedding):
            with patch("my_garage.services.context_service.get_collection") as mc:
                mc.return_value.find.return_value = mock_chunks
                result = context_service.retrieve_relevant_docs("service", k=2)

        assert len(result) == 2
        assert all(isinstance(r, str) for r in result)

    def test_respects_k_limit(self, context_service):
        """The number of retrieved docs is at most k."""
        mock_embedding = [1.0] + [0.0] * 767
        mock_chunks = [
            {"content": f"Chunk {i}", "embedding": [float(i % 2)] + [0.0] * 767}
            for i in range(10)
        ]
        with patch.object(context_service, "_embed_query", return_value=mock_embedding):
            with patch("my_garage.services.context_service.get_collection") as mc:
                mc.return_value.find.return_value = mock_chunks
                result = context_service.retrieve_relevant_docs("query", k=3)

        assert len(result) <= 3

    def test_graceful_on_mongo_timeout(self, context_service):
        from pymongo.errors import ServerSelectionTimeoutError

        mock_embedding = [1.0] + [0.0] * 767
        with patch.object(context_service, "_embed_query", return_value=mock_embedding):
            with patch("my_garage.services.context_service.get_collection") as mc:
                mc.side_effect = ServerSelectionTimeoutError("timeout")
                result = context_service.retrieve_relevant_docs("anything")

        assert result == []

    def test_graceful_on_embedding_failure(self, context_service):
        with patch.object(
            context_service, "_embed_query", side_effect=Exception("API down")
        ):
            result = context_service.retrieve_relevant_docs("some query")
        assert result == []
