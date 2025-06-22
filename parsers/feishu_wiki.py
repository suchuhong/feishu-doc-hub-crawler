"""
parsers.feishu_wiki
~~~~~~~~~~~~~~~~~~~
使用 Playwright 加载 Feishu Wiki，截图上传 OSS，并生成向量切片与摘要。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError

from util.oss_util import OSSUtil
from util.visited_decorator import skip_if_visited
from util.llm_util import LLMUtil

logger = logging.getLogger(__name__)
oss = OSSUtil()
_llm = LLMUtil()                           # 全局单例

MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #
async def _capture_and_upload_screenshot(page, url: str) -> tuple[str, str]:
    """截图并上传 OSS，返回 screenshot_url, thumbnail_url"""
    screenshot_path = (
        "./"
        + url.replace("https://", "")
        .replace("http://", "")
        .replace("/", "")
        .replace(".", "-")
        + ".png"
    )
    await page.screenshot(path=screenshot_path, full_page=True)

    image_key = oss.get_default_file_key(url)
    screenshot_url = oss.upload_file_to_r2(screenshot_path, image_key)
    thumbnail_url = oss.generate_thumbnail_image(url, image_key)
    return screenshot_url, thumbnail_url


async def _extract_feishu_wiki_data(page, url: str) -> Dict[str, Any]:
    """提取 Feishu Wiki 内容（标题、正文、超链接）"""
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title else "飞书 Wiki"

    # 主内容
    main_content = soup.find("div", {"class": "wiki-render-wrapper"})
    if main_content:
        content = main_content.get_text("\n", strip=True)
    else:
        content = soup.get_text("\n", strip=True)

    # 有效外链
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        if href.startswith("http"):
            links.append({"text": text or "[无文字链接]", "href": href})

    return {
        "title": title,
        "description": content[:200] if content else "暂无内容",
        "detail": content,
        "tags": ["feishu", "wiki"],
        "links": links,
        "url": url,
    }


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
@skip_if_visited
async def parse_feishu_wiki(url: str) -> Dict[str, Any]:
    """主解析器：加载网页 → 抓取内容 → 截图上传 → LLM 切片/摘要"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent=MODERN_UA,
                locale="zh-CN",
                viewport={"width": 1920, "height": 1080, "deviceScaleFactor": 2},
                java_script_enabled=True,
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=20000, wait_until="networkidle")
                await page.wait_for_timeout(4000)

                screenshot_url, thumbnail_url = await _capture_and_upload_screenshot(
                    page, url
                )
                wiki_data = await _extract_feishu_wiki_data(page, url)

                # LLM 处理
                chunks: List[Dict[str, Any]] = _llm.split_and_embed(
                    wiki_data["detail"]
                )
                summary: str = _llm.summarize_md(wiki_data["detail"])

                return {
                    **wiki_data,
                    "screenshot_data": screenshot_url,
                    "screenshot_thumbnail_data": thumbnail_url,
                    "chunks": chunks,
                    "summary": summary,
                }

            except TimeoutError:
                return {
                    "title": "加载超时",
                    "description": "Wiki 页面加载超时。",
                    "detail": "",
                    "screenshot_data": "",
                    "screenshot_thumbnail_data": "",
                    "tags": ["feishu", "wiki", "error"],
                    "links": [],
                    "chunks": [],
                    "summary": "",
                    "url": url,
                }
            finally:
                await page.close()
                await context.close()
                await browser.close()

    except Exception as e:
        logger.exception("飞书 Wiki 解析失败")
        return {
            "title": "Wiki 解析失败",
            "description": f"发生错误: {str(e)}",
            "detail": "",
            "screenshot_data": "",
            "screenshot_thumbnail_data": "",
            "tags": ["feishu", "wiki", "error"],
            "links": [],
            "chunks": [],
            "summary": "",
            "url": url,
        }
