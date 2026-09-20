import os
import requests
import httpx
from dotenv import load_dotenv

load_dotenv()

JINA_API_KEY = os.getenv("JINA_API_KEY")
MODEL_NAME = "jina-reranker-v2-base-multilingual"


def _fallback_score(chunk: dict) -> float:
    """Combine available retrieval scores when the cross-encoder is unavailable."""
    vector = chunk.get("vector_score")
    bm25 = chunk.get("bm25_score")
    scores = []
    if isinstance(vector, (int, float)):
        scores.append(float(vector))
    if isinstance(bm25, (int, float)):
        # BM25 is unbounded; compress into a comparable range
        scores.append(float(bm25) / (1.0 + float(bm25)))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _fallback_rerank(chunks: list, top_k: int) -> list:
    scored = []
    for chunk in chunks:
        item = dict(chunk)
        item["rerank_score"] = _fallback_score(item)
        item["rerank_fallback"] = True
        scored.append(item)
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[:top_k]


def rerank_chunks(
    query: str,
    chunks: list,
    top_k: int = 5,
):
    if not chunks:
        return []

    if not JINA_API_KEY:
        print("[reranker] JINA_API_KEY missing; using vector/BM25 fallback")
        return _fallback_rerank(chunks, top_k)

    documents = [chunk["text"] for chunk in chunks]

    try:
        response = requests.post(
            "https://api.jina.ai/v1/rerank",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {JINA_API_KEY}",
            },
            json={
                "model": MODEL_NAME,
                "query": query,
                "documents": documents,
                "return_documents": False,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json()["results"]

        scored_chunks = []
        for result in results:
            idx = result["index"]
            chunk = dict(chunks[idx])
            chunk["rerank_score"] = result["relevance_score"]
            scored_chunks.append(chunk)

        scored_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_chunks[:top_k]
    except Exception as e:
        print(f"[reranker] Jina rerank failed ({e}); using vector/BM25 fallback")
        return _fallback_rerank(chunks, top_k)


async def rerank_chunks_async(
    query: str,
    chunks: list,
    top_k: int = 5,
):
    if not chunks:
        return []

    if not JINA_API_KEY:
        print("[reranker] JINA_API_KEY missing; using vector/BM25 fallback")
        return _fallback_rerank(chunks, top_k)

    documents = [chunk["text"] for chunk in chunks]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.jina.ai/v1/rerank",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {JINA_API_KEY}",
                },
                json={
                    "model": MODEL_NAME,
                    "query": query,
                    "documents": documents,
                    "return_documents": False,
                },
                timeout=30.0,
            )
        response.raise_for_status()
        results = response.json()["results"]

        scored_chunks = []
        for result in results:
            idx = result["index"]
            chunk = dict(chunks[idx])
            chunk["rerank_score"] = result["relevance_score"]
            scored_chunks.append(chunk)

        scored_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_chunks[:top_k]
    except Exception as e:
        print(f"[reranker] Jina rerank failed ({e}); using vector/BM25 fallback")
        return _fallback_rerank(chunks, top_k)
