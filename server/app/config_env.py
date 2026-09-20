"""Application environment bootstrap.

Loads `server/.env` via an absolute path so Uvicorn workers, background
tasks, and async request handlers all see the same variables regardless of
process cwd or import order.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# server/app/config_env.py → server/
SERVER_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = SERVER_ROOT / ".env"

_loaded_mtime: float | None = None


def load_app_env(*, force: bool = False) -> Path:
    """Load server/.env into os.environ.

    If GEMINI_API_KEY is still missing/blank after a non-overriding load
    (e.g. an empty value was inherited from the parent process), reload with
    override=True so the file wins.
    """
    global _loaded_mtime

    path = ENV_FILE
    mtime = path.stat().st_mtime if path.is_file() else None

    if not force and _loaded_mtime is not None and mtime == _loaded_mtime:
        if (os.getenv("GEMINI_API_KEY") or "").strip():
            return path

    if path.is_file():
        load_dotenv(path, override=False)
        if not (os.getenv("GEMINI_API_KEY") or "").strip():
            load_dotenv(path, override=True)
        _loaded_mtime = mtime
    else:
        # Fall back to cwd discovery for unusual layouts; still idempotent.
        load_dotenv(override=False)
        _loaded_mtime = mtime

    return path


def get_gemini_api_key() -> str:
    """Return a non-empty Gemini API key, loading env first if needed."""
    load_app_env()
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        # .env may have been edited after process start — force one reload.
        load_app_env(force=True)
        key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to server/.env and ensure the "
            "API process can read that file."
        )
    return key
