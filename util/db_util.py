# util/db_util.py
import sqlite3
from pathlib import Path
from typing import Dict, Any

_DB_PATH = Path(__file__).parent / "data.db"
_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS docs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT UNIQUE,
    title       TEXT,
    description TEXT,
    detail      TEXT,
    tags        TEXT,
    links       TEXT,         -- Wiki 才有；Doc 留空
    screenshot  TEXT,
    thumb       TEXT,
    summary     TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(_TABLE_SQL)
    return conn

def upsert_doc(record: Dict[str, Any]) -> None:
    """
    把解析结果写入 docs 表；url 唯一 → 已存在则更新。
    仅选常用字段，其余可按需加列。
    """
    conn = _get_conn()
    with conn:
        conn.execute(
            """
            INSERT INTO docs
                (url, title, description, detail, tags, links,
                 screenshot, thumb, summary)
            VALUES
                (:url, :title, :description, :detail, :tags, :links,
                 :screenshot_data, :screenshot_thumbnail_data, :summary)
            ON CONFLICT(url) DO UPDATE SET
                title       = excluded.title,
                description = excluded.description,
                detail      = excluded.detail,
                tags        = excluded.tags,
                links       = excluded.links,
                screenshot  = excluded.screenshot,
                thumb       = excluded.thumb,
                summary     = excluded.summary;
            """,
            {
                **record,
                "tags": ",".join(record.get("tags", [])),
                "links": json_dumps(record.get("links")),  # helper below
            },
        )

def json_dumps(obj):
    import json, typing as t
    if obj is None or isinstance(obj, (str, bytes)):
        return obj
    return json.dumps(obj, ensure_ascii=False)
