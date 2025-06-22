# util/visited_util.py
import sqlite3
from pathlib import Path


class VisitedRegistry:
    """
    记录已抓取过的 URL，避免重复处理
    - 数据库存放在与本文件同级目录下的 visited.db
    - 表结构：visited(url TEXT PRIMARY KEY)
    """

    DB_PATH = Path(__file__).parent / "visited.db"

    def __init__(self) -> None:
        self._ensure_table()

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _ensure_table(self) -> None:
        """第一次使用时建表；若已存在则跳过"""
        conn = sqlite3.connect(self.DB_PATH)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS visited (url TEXT PRIMARY KEY)"
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #
    def has(self, url: str) -> bool:
        """URL 是否已记录"""
        conn = sqlite3.connect(self.DB_PATH)
        try:
            cur = conn.execute("SELECT 1 FROM visited WHERE url = ? LIMIT 1", (url,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def add(self, url: str) -> None:
        """插入 URL；已存在时忽略"""
        conn = sqlite3.connect(self.DB_PATH)
        try:
            conn.execute("INSERT OR IGNORE INTO visited (url) VALUES (?)", (url,))
            conn.commit()
        finally:
            conn.close()
