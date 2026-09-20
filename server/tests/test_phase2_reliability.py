"""Phase 2 reliability / cache / RAG unit tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

for _mod in (
    "yt_dlp",
    "imageio_ffmpeg",
    "qdrant_client",
    "qdrant_client.models",
    "rank_bm25",
    "google",
    "google.genai",
    "google.genai.types",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


class TestRerankFallback(unittest.TestCase):
    def test_fallback_when_jina_key_missing(self):
        with patch.dict(os.environ, {"JINA_API_KEY": ""}, clear=False):
            import importlib
            import app.retrieval.reranker as reranker

            importlib.reload(reranker)
            chunks = [
                {"id": "1", "text": "a", "vector_score": 0.9, "bm25_score": 1.0},
                {"id": "2", "text": "b", "vector_score": 0.1, "bm25_score": 10.0},
            ]
            out = reranker.rerank_chunks("q", chunks, top_k=1)
            self.assertEqual(len(out), 1)
            self.assertTrue(out[0].get("rerank_fallback"))
            self.assertIn("rerank_score", out[0])

    def test_fallback_on_http_error(self):
        import app.retrieval.reranker as reranker

        chunks = [
            {"id": "1", "text": "alpha", "vector_score": 0.8},
            {"id": "2", "text": "beta", "vector_score": 0.2},
        ]
        with patch.object(reranker, "JINA_API_KEY", "fake-key"):
            with patch.object(reranker.requests, "post", side_effect=RuntimeError("boom")):
                out = reranker.rerank_chunks("q", chunks, top_k=2)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(c.get("rerank_fallback") for c in out))
        self.assertGreaterEqual(out[0]["rerank_score"], out[1]["rerank_score"])


class TestCreateCollectionSafety(unittest.TestCase):
    def test_mismatch_does_not_delete(self):
        import app.vectorstore.store as store

        fake_client = MagicMock()
        coll = MagicMock()
        coll.name = store.COLLECTION_NAME
        fake_client.get_collections.return_value.collections = [coll]

        info = MagicMock()
        info.config.params.vectors.distance = "Cosine"
        info.config.params.vectors.size = 768
        fake_client.get_collection.return_value = info

        with patch.object(store, "client", fake_client):
            with self.assertRaises(RuntimeError):
                store.create_collection(1024)
            fake_client.delete_collection.assert_not_called()


class TestJobPersistence(unittest.TestCase):
    def test_job_survives_memory_clear(self):
        from app.api import upload as upload_mod

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(upload_mod, "JOBS_DIR", tmp):
                upload_mod.job_store.clear()
                job = upload_mod.Job(
                    job_id="persist-1",
                    filename="a.pdf",
                    user_id="user_a",
                    status=upload_mod.JobStatus.PROCESSING,
                )
                upload_mod._register_job(job)

                upload_mod.job_store.clear()
                loaded = upload_mod._get_job("persist-1")
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.user_id, "user_a")
                self.assertEqual(loaded.status, upload_mod.JobStatus.PROCESSING)
                self.assertTrue(os.path.exists(os.path.join(tmp, "persist-1.json")))


class TestHandlersResolve(unittest.TestCase):
    def test_resolve_includes_docx_pptx(self):
        from app.agent import handlers

        with tempfile.TemporaryDirectory() as tmp:
            parsed = os.path.join(tmp, "data", "parsed", "u1")
            cleaned = os.path.join(tmp, "data", "cleaned_pdfs", "u1")
            os.makedirs(parsed)
            os.makedirs(cleaned)
            open(os.path.join(parsed, "deck.json"), "w").close()
            open(os.path.join(parsed, "memo.json"), "w").close()
            open(os.path.join(cleaned, "deck.pptx"), "w").close()
            open(os.path.join(cleaned, "memo.docx"), "w").close()

            with patch.object(handlers, "PARSED_DIR", os.path.join(tmp, "data", "parsed")):
                with patch.object(handlers, "BASE_DIR", tmp):
                    files = handlers._resolve_active_files([], "u1")
            self.assertIn("deck.pptx", files)
            self.assertIn("memo.docx", files)


class TestFairSelection(unittest.TestCase):
    def test_min_per_file_selection_logic(self):
        """Mirror retrieve_per_file fair selection without Qdrant."""
        from collections import defaultdict

        selected_files = ["a.pdf", "b.pdf"]
        scored = [
            {"id": "a1", "source_file": "a.pdf", "rerank_score": 0.99},
            {"id": "a2", "source_file": "a.pdf", "rerank_score": 0.98},
            {"id": "a3", "source_file": "a.pdf", "rerank_score": 0.97},
            {"id": "b1", "source_file": "b.pdf", "rerank_score": 0.5},
            {"id": "b2", "source_file": "b.pdf", "rerank_score": 0.4},
        ]
        min_per_file = 1
        rerank_top_k = 3
        target_size = max(rerank_top_k, min_per_file * len(selected_files))

        by_file = defaultdict(list)
        for c in scored:
            by_file[c["source_file"]].append(c)

        selected = []
        seen = set()
        for filename in selected_files:
            for chunk in by_file.get(filename, [])[:min_per_file]:
                if chunk["id"] not in seen:
                    selected.append(chunk)
                    seen.add(chunk["id"])
        for chunk in scored:
            if len(selected) >= target_size:
                break
            if chunk["id"] not in seen:
                selected.append(chunk)
                seen.add(chunk["id"])

        sources = {c["source_file"] for c in selected}
        self.assertEqual(sources, {"a.pdf", "b.pdf"})
        self.assertEqual(len(selected), 3)


class TestCacheRequiresVectors(unittest.TestCase):
    def test_is_cached_false_without_vectors(self):
        from app.ingestion import cache as cache_mod

        with tempfile.TemporaryDirectory() as tmp:
            user = "u1"
            parsed = os.path.join(tmp, "parsed.json")
            cleaned_dir = os.path.join(tmp, "data", "cleaned_pdfs", user)
            os.makedirs(cleaned_dir)
            filename = "doc.pdf"
            open(parsed, "w").close()
            open(os.path.join(cleaned_dir, filename), "w").close()

            with patch.object(cache_mod, "BASE_DIR", tmp):
                with patch.object(cache_mod, "CACHE_DIR", os.path.join(tmp, "cache")):
                    cache_mod.set_cached_entry("abc", filename, parsed, user_id=user)
                    with patch(
                        "app.vectorstore.store.has_vectors_for_file",
                        return_value=False,
                    ):
                        self.assertFalse(cache_mod.is_cached("abc", user_id=user))
                    with patch(
                        "app.vectorstore.store.has_vectors_for_file",
                        return_value=True,
                    ):
                        self.assertTrue(cache_mod.is_cached("abc", user_id=user))


if __name__ == "__main__":
    unittest.main()
