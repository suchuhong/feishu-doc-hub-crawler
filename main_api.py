import logging
import os
import sys
import re
from typing import List, Optional

import requests
from fastapi import FastAPI, Header, BackgroundTasks, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from website_crawler import WebsitCrawler
from parsers.feishu import parse_feishu_doc
from parsers.feishu_wiki import parse_feishu_wiki

# ⬇️ 安装 googlesearch-python: pip install googlesearch-python
from googlesearch import search

# 初始化
app = FastAPI()
website_crawler = WebsitCrawler()
load_dotenv()
system_auth_secret = os.getenv('AUTH_SECRET')

# 日志设置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ----------- 请求模型 ------------
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


# ---------- 工具函数 --------------
def validate_authorization(authorization):
    if not authorization:
        raise HTTPException(status_code=400, detail="Missing Authorization header")
    if 'Bearer ' + system_auth_secret != authorization:
        raise HTTPException(status_code=401, detail="Authorization is error")


def is_valid_feishu_link(url: str) -> bool:
    url = url.strip()
    return re.match(r"^https://[\w\-]+\.feishu\.cn/(wiki|docx|sheets)/[\w\-]+", url) is not None

def discover_feishu_links(keyword: str, max_results: int = 5) -> List[str]:
    from googlesearch import search
    query = f"{keyword} site:feishu.cn/wiki OR site:feishu.cn/sheets OR site:feishu.cn/docx"

    raw_results = list(search(query, num_results=max_results))
    print("Raw search results:")
    for url in raw_results:
        print(url, "=>", is_valid_feishu_link(url))

    valid_links = [url for url in raw_results if is_valid_feishu_link(url)]
    print("Valid links:", valid_links)
    return valid_links


# ---------- 同步处理接口 ----------
@app.post('/site/crawl')
async def scrape(request: URLRequest, authorization: Optional[str] = Header(None)):
    url = request.url
    tags = request.tags
    languages = request.languages

    if system_auth_secret:
        validate_authorization(authorization)

    result = None
    if "feishu.cn/docx/" in url:
        result = await parse_feishu_doc(url.strip())
    elif "feishu.cn/wiki/" in url:
        result = await parse_feishu_wiki(url.strip())
    else:
        result = await website_crawler.scrape_website(url.strip(), tags, languages)

    code = 200 if result else 10001
    msg = "success" if result else "fail"

    return {
        "code": code,
        "msg": msg,
        "data": result
    }


# ---------- 异步处理接口 ----------
@app.post('/site/crawl_async')
async def scrape_async(background_tasks: BackgroundTasks, request: AsyncURLRequest,
                       authorization: Optional[str] = Header(None)):
    if system_auth_secret:
        validate_authorization(authorization)

    background_tasks.add_task(async_worker, request.url.strip(), request.tags,
                              request.languages, request.callback_url, request.key)
    return {"code": 200, "msg": "success"}


async def async_worker(url, tags, languages, callback_url, key):
    result = await website_crawler.scrape_website(url.strip(), tags, languages)
    try:
        logger.info(f'callback begin: {callback_url}')
        response = requests.post(callback_url, json=result, headers={'Authorization': f'Bearer {key}'})
        if response.status_code != 200:
            logger.error(f'callback error: {response.text}')
        else:
            logger.info('callback success')
    except Exception as e:
        logger.error(f'callback exception: {e}')


# ---------- 新增公开链接发现接口 ----------
@app.post('/site/crawl_discover')
async def crawl_discover(request: DiscoverRequest, authorization: Optional[str] = Header(None)):
    if system_auth_secret:
        validate_authorization(authorization)

    try:
        urls = discover_feishu_links(request.keyword, request.max_results or 5)
        # 输出 urls 的 值
        for url in urls:
            print(url)
            print("url --------------------------------")
        results = []
        for url in urls:
            print(url)
            if "feishu.cn/docx" in url:
                res = await parse_feishu_doc(url)
            elif "feishu.cn/wiki" in url:
                res = await parse_feishu_wiki(url.strip())
            else:
                res = await website_crawler.scrape_website(url, request.tags, request.languages)
            if res:
                results.append(res)

        return {"code": 200, "msg": "success", "data": results}

    except Exception as e:
        logger.error(f"crawl_discover error: {e}")
        return {"code": 10001, "msg": "处理异常，请稍后重试", "data": []}


# ---------- 启动服务 ----------
if __name__ == '__main__':
    import uvicorn
    print("当前 Python 解释器路径:", sys.executable)
    uvicorn.run(app, host="0.0.0.0", port=8040)
