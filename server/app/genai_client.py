"""Shared google-genai Client for embeddings and chat.

One long-lived Client per process avoids:
- missing API key from cwd-relative dotenv / late load_dotenv
- ephemeral Client GC triggering BaseApiClient.aclose() AttributeError
"""

from __future__ import annotations

from google import genai

from app.config_env import get_gemini_api_key, load_app_env

_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """Return a process-wide Client constructed with an explicit API key."""
    global _client
    load_app_env()
    if _client is None:
        _client = genai.Client(api_key=get_gemini_api_key())
    return _client
