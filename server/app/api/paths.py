"""Safe path resolution for tenant-scoped file access."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, status


def sanitize_filename(filename: str) -> str:
    """
    Return a single path segment suitable for joining under a user directory.

    Rejects empty names, absolute paths, drive letters, and any segment that
    would escape via '..' or nested separators.
    """
    if filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    raw = filename.strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Normalize separators then take the final component only
    normalized = raw.replace("\\", "/")
    base = os.path.basename(normalized)

    if not base or base in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    if os.path.isabs(base) or (len(base) >= 2 and base[1] == ":"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    # Reject if basename still contains traversal or separator residue
    if ".." in base or "/" in base or "\\" in base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    return base


def resolve_under_user_dir(
    base_dir: str,
    *parts: str,
    filename: Optional[str] = None,
) -> str:
    """
    Join base_dir/parts[/filename] and ensure the resolved path stays under base_dir.

    `filename`, when provided, is sanitized first. Intermediate `parts` must not
    contain '..' segments.
    """
    for part in parts:
        if part in {".", ".."} or ".." in part.replace("\\", "/").split("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path",
            )

    safe_name = sanitize_filename(filename) if filename is not None else None
    candidate_parts = list(parts)
    if safe_name is not None:
        candidate_parts.append(safe_name)

    root = os.path.abspath(base_dir)
    resolved = os.path.abspath(os.path.join(root, *candidate_parts))

    try:
        common = os.path.commonpath([root, resolved])
    except ValueError:
        # Different drives on Windows
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path",
        )

    if common != root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path",
        )

    return resolved
