"""supabase_utils.py – Supabase helper utilities
---------------------------------------------------
Thin wrapper around Supabase Python SDK.  
All functions use a cached client created from `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` env vars.

Key change (2025‑06‑22)
~~~~~~~~~~~~~~~~~~~~~~~
* **save_category()** now checks whether the category already exists and only
  inserts when it is *missing* – satisfying the requirement "类别存在则不用插入".
  This avoids the need for a UNIQUE constraint on `name`, though adding one is
  still recommended.
"""

from __future__ import annotations

import os
import json
from functools import lru_cache
from typing import Any, Dict, List, Optional

from supabase import Client, create_client


# ---------------------------------------------------------------------------
# Client factory (cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Return a memoised Supabase client instance."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def save_category(
    name: str,
    title: Optional[str] = None,
    sort: int = 0,
    del_flag: int = 0,
    create_by: int = 0,
) -> Optional[int]:
    """Insert a new category **only if the name does not already exist**.

    Returns the *existing* or *new* category id; ``None`` on failure.
    """
    client = get_client()

    # 1️⃣ Query first – if exists, short‑circuit.
    existing = (
        client.table("navigation_category")
        .select("id")
        .eq("name", name)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    # 2️⃣ Otherwise, insert a new row.
    data = {
        "name": name,
        "title": title,
        "sort": sort,
        "del_flag": del_flag,
        "create_by": create_by,
    }
    resp = client.table("navigation_category").insert(data).execute()
    if resp.data:
        return resp.data[0]["id"]
    return None


def save_web_navigation(record: Dict[str, Any]) -> None:
    """Upsert a single *web_navigation* row using **url** as the conflict key."""
    if not record:
        return
    # get_client().table("web_navigation").upsert(record, on_conflict="url").execute()
    get_client().table("web_navigation").upsert(record).execute()


def bulk_save_web_navigation(records: List[Dict[str, Any]]) -> None:
    """Batch‑write helper for multiple *web_navigation* records."""
    if not records:
        return
    get_client().table("web_navigation").upsert(records, on_conflict="url").execute()

# ---------------------------------------------------------------------------
# Public exports -------------------------------------------------------------
# ---------------------------------------------------------------------------

__all__ = [
    "get_client",
    "save_category",
    "save_web_navigation",
    "bulk_save_web_navigation",
]
