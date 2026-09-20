import os
from qdrant_client import QdrantClient

from app.config_env import load_app_env

load_app_env()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# cloud_inference is only for Qdrant-hosted model inference on Document inputs.
# Docify upserts/searchs numeric vectors from Gemini, so keep this False.
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    cloud_inference=False,
)
