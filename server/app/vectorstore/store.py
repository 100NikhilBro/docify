import time
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.vectorstore.qdrant_client import client


COLLECTION_NAME = "pdf_rag"


def _ensure_payload_indexes():
    try:
        client.create_payload_index(COLLECTION_NAME, "user_id", PayloadSchemaType.KEYWORD)
    except Exception:
        pass
    try:
        client.create_payload_index(COLLECTION_NAME, "source_file", PayloadSchemaType.KEYWORD)
    except Exception:
        pass


def create_collection(vector_size: int):
    """
    Ensure the shared collection exists with the expected DOT + size config.

    Never deletes an existing collection. On size/distance mismatch, raises so
    operators can migrate deliberately instead of wiping all tenants.
    """
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)

    if exists:
        try:
            info = client.get_collection(COLLECTION_NAME)
            vectors_config = info.config.params.vectors

            current_distance = None
            current_size = None

            if hasattr(vectors_config, "distance"):
                current_distance = vectors_config.distance
                current_size = vectors_config.size
            elif isinstance(vectors_config, dict) and "distance" in vectors_config:
                current_distance = vectors_config["distance"]
                current_size = vectors_config["size"]

            if current_distance == Distance.DOT and current_size == vector_size:
                _ensure_payload_indexes()
                return

            raise RuntimeError(
                f"Qdrant collection '{COLLECTION_NAME}' exists with incompatible "
                f"config (distance={current_distance}, size={current_size}); "
                f"expected Distance.DOT and size={vector_size}. "
                f"Refusing to delete/recreate to protect existing tenant data."
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to verify Qdrant collection '{COLLECTION_NAME}': {e}"
            ) from e

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.DOT,
        ),
    )
    _ensure_payload_indexes()
    print(f"Qdrant collection '{COLLECTION_NAME}' created with Distance.DOT")


def has_vectors_for_file(user_id: str, source_file: str) -> bool:
    """Return True if at least one point exists for this user + source file."""
    if not source_file:
        return False
    try:
        collections = client.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            return False

        result = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    FieldCondition(
                        key="source_file", match=MatchValue(value=source_file)
                    ),
                ]
            ),
            exact=True,
        )
        return (result.count or 0) > 0
    except Exception as e:
        print(f"[store] has_vectors_for_file failed: {e}")
        return False


def delete_chunks_for_file(user_id: str, source_file: str) -> None:
    """Delete all points for a user/source_file pair before re-indexing."""
    if not source_file:
        return
    try:
        collections = client.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            return
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    FieldCondition(
                        key="source_file", match=MatchValue(value=source_file)
                    ),
                ]
            ),
        )
        print(
            f"[store] Deleted existing points for user_id={user_id} "
            f"source_file={source_file}"
        )
    except Exception as e:
        print(f"[store] delete_chunks_for_file failed: {e}")


def store_chunks(
    chunks,
    embeddings,
    user_id="default_tenant",
    retries=3,
    delay=2.0,
    replace_existing=True,
):
    if not chunks:
        return

    source_file = chunks[0].get("source_file")
    if replace_existing and source_file:
        delete_chunks_for_file(user_id, source_file)

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        payload = dict(chunk)
        payload["user_id"] = user_id
        point = PointStruct(
            id=chunk["id"],
            vector=embedding,
            payload=payload,
        )
        points.append(point)

    for attempt in range(retries):
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
            )
            print(f"Stored {len(points)} chunks with user_id: {user_id}")
            return
        except Exception as e:
            if attempt == retries - 1:
                raise e
            print(
                f"[store] Qdrant upsert attempt {attempt + 1} failed: {e}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
            delay *= 2
