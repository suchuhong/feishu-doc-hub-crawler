"""
High‑level HTTP API for discovering and crawling Feishu (Lark) public docs
---------------------------------------------------------------------------
This version persists every crawl result directly to Supabase (`navigation_category`
& `web_navigation`) via the helper functions in `util.supabase_utils`.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from typing import List, Optional, Set

import requests
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# Supabase helpers – replace legacy upsert_doc
# --------------------------------------------------------------------------- #
from util.supabase_utils import save_category, save_web_navigation

# ---------- 初始化日志，必须在任何 logger 声明之前 ----------
from util.logging_util import init_logging

init_logging()  # 彩色控制台 + 滚动文件等配置
logger = logging.getLogger(__name__)  # 之后所有模块沿用

# ---------- 业务依赖 ----------
from website_crawler import WebsitCrawler
from parsers.feishu import parse_feishu_doc
from parsers.feishu_wiki import parse_feishu_wiki

# ⬇️ pip install googlesearch-python
from googlesearch import search

# 持久化去重
from util.visited_util import VisitedRegistry

# --------------------------------------------------------------------------- #
# FastAPI App – bootstrap
# --------------------------------------------------------------------------- #

app = FastAPI()
website_crawler = WebsitCrawler()
load_dotenv()
system_auth_secret = os.getenv("AUTH_SECRET")


# ------------------------------- 中间件 ----------------------------------- #
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    统一请求-响应日志，附加 trace-id，便于链路排障。
    """
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    logger.info("%s - %s %s", trace_id, request.method, request.url.path)
    response = await call_next(request)
    logger.info("%s - %s", trace_id, response.status_code)
    response.headers["X-Trace-Id"] = trace_id
    return response


# --------------------------------------------------------------------------- #
# Data Models
# --------------------------------------------------------------------------- #
class URLRequest(BaseModel):
    url: str
    tags: Optional[List[str]] = None
    languages: Optional[List[str]] = None


class AsyncURLRequest(URLRequest):
    callback_url: str
    key: str


class DiscoverRequest(BaseModel):
    keyword: str
    max_results: Optional[int] = 5
    tags: Optional[List[str]] = None
    languages: Optional[List[str]] = None


# --------------------------------------------------------------------------- #
# Helper Functions
# --------------------------------------------------------------------------- #

def validate_authorization(authorization: Optional[str]) -> None:
    if not authorization:
        raise HTTPException(status_code=400, detail="Missing Authorization header")
    if "Bearer " + system_auth_secret != authorization:
        raise HTTPException(status_code=401, detail="Authorization is error")


def is_valid_feishu_link(url: str) -> bool:
    """
    粗粒度校验：判断 URL 是否形如 Feishu 公共 Wiki / Doc / Sheet。
    """
    url_l = url.strip().lower()
    return (
        url_l.startswith("https://")
        and ".feishu.cn" in url_l
        and ("/wiki/" in url_l or "/docx/" in url_l or "/sheets/" in url_l)
    )


def discover_feishu_links(keyword: str, max_results: int = 5) -> List[str]:
    """
    使用 Google 查找指定关键字的 Feishu 链接，并排除：
      1. URL 结构不合法的结果
      2. 已经抓取过的结果（VisitedRegistry）

    返回值数量 ≤ max_results，均为“全新”合法链接。
    """
    registry = VisitedRegistry()

    query = (
        f"{keyword} "
        f"site:feishu.cn/wiki OR site:feishu.cn/sheets OR site:feishu.cn/docx"
    )
    # 预抓更多条目，给过滤留余量
    raw_results: List[str] = list(search(query, num_results=max_results * 3))

    logger.info("Raw search results:")
    for url in raw_results:
        logger.info(
            "%s => valid? %s | visited? %s",
            url,
            is_valid_feishu_link(url),
            registry.has(url),
        )

    valid_links: List[str] = []
    seen: Set[str] = set()

    for url in raw_results:
        if url in seen:
            continue
        seen.add(url)

        if not is_valid_feishu_link(url):
            continue
        if registry.has(url):
            continue

        valid_links.append(url)
        if len(valid_links) >= max_results:
            break

    logger.info("Valid & new links: %s", valid_links)
    return valid_links


# --------------------------------------------------------------------------- #
# Supabase persistence helper
# --------------------------------------------------------------------------- #

def persist_to_supabase(record: dict) -> None:
    """Upsert *both* navigation_category & web_navigation through supabase_utils."""
    if not record:
        return
    
    cat_name = "ai-doc"
    save_category(
        name=cat_name,
        title="AI DOC",
        sort=0,
    )

    logger.info("save_category: %s", cat_name)

    # ② 主表 – 字段映射
    save_web_navigation(
        {
            "name": record.get("title"),
            "title": record.get("title"),
            # 新老模型字段对齐：summary / description ≈ content
            "content": record.get("summary")
            or record.get("description")
            or record.get("content"),
            "detail": record.get("detail"),
            "url": record.get("url"),
            # screenshot/thumbnail 兼容
            "image_url": record.get("screenshot_data") or record.get("image_url"),
            "thumbnail_url": record.get("screenshot_thumbnail_data")
            or record.get("thumbnail_url"),
            # links 单独序列化，若无则存整条记录方便调试
            "website_data": json.dumps(
                record.get("links") if record.get("links") is not None else record,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "collection_time": record.get("collection_time"),
            "star_rating": record.get("star_rating") or 0,
            "tag_name": ",".join(record.get("tags", []))
            if isinstance(record.get("tags"), list)
            else (record.get("tag_name") or None),
            "category_name": cat_name,
        }
    )


# --------------------------------------------------------------------------- #
# Synchronous Endpoint
# --------------------------------------------------------------------------- #
@app.post("/site/crawl")
async def scrape(request: URLRequest, authorization: Optional[str] = Header(None)):
    if system_auth_secret:
        validate_authorization(authorization)

    url = request.url.strip()
    tags = request.tags
    languages = request.languages

    # 解析分流
    if "feishu.cn/docx/" in url:
        result = await parse_feishu_doc(url)
    elif "feishu.cn/wiki/" in url:
        result = await parse_feishu_wiki(url)
    else:
        result = await website_crawler.scrape_website(url, tags, languages)

    if result:
        persist_to_supabase(result)

    code = 200 if result else 10001
    msg = "success" if result else "fail"
    return {"code": code, "msg": msg, "data": result}


# --------------------------------------------------------------------------- #
# Asynchronous Endpoint
# --------------------------------------------------------------------------- #
@app.post("/site/crawl_async")
async def scrape_async(
    background_tasks: BackgroundTasks,
    request: AsyncURLRequest,
    authorization: Optional[str] = Header(None),
):
    if system_auth_secret:
        validate_authorization(authorization)

    background_tasks.add_task(
        async_worker,
        request.url.strip(),
        request.tags,
        request.languages,
        request.callback_url,
        request.key,
    )
    return {"code": 200, "msg": "success"}


async def async_worker(url, tags, languages, callback_url, key):
    result = await website_crawler.scrape_website(url, tags, languages)
    if result:
        persist_to_supabase(result)
    try:
        logger.info("callback begin: %s", callback_url)
        response = requests.post(
            callback_url, json=result, headers={"Authorization": f"Bearer {key}"}
        )
        if response.status_code != 200:
            logger.error("callback error: %s", response.text)
        else:
            logger.info("callback success")
    except Exception as e:
        logger.error("callback exception: %s", e)


# --------------------------------------------------------------------------- #
# Discovery Endpoint
# --------------------------------------------------------------------------- #
@app.post("/site/crawl_discover")
async def crawl_discover(
    request: DiscoverRequest, authorization: Optional[str] = Header(None)
):
    if system_auth_secret:
        validate_authorization(authorization)

    try:
        urls = discover_feishu_links(request.keyword, request.max_results or 5)

        results = []
        for url in urls:
            if "feishu.cn/docx" in url:
                res = await parse_feishu_doc(url)
            elif "feishu.cn/wiki" in url:
                res = await parse_feishu_wiki(url)
            else:
                res = await website_crawler.scrape_website(
                    url, request.tags, request.languages
                )
            if res:
                persist_to_supabase(res)
                results.append(res)

        return {"code": 200, "msg": "success", "data": results}

    except Exception as e:
        logger.error("crawl_discover error: %s", e)
        return {"code": 10001, "msg": "处理异常，请稍后重试", "data": []}


# --------------------------------------------------------------------------- #
# Entrypoint – Local dev only
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import uvicorn

    print("当前 Python 解释器路径:", sys.executable)
    uvicorn.run(app, host="0.0.0.0", port=8040)
