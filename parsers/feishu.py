"""
parsers.feishu
~~~~~~~~~~~~~~
使用 Playwright 加载 Feishu Docx，截图上传 OSS，并生成分段向量与摘要。
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
_llm = LLMUtil()  # 全局单例

MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #
async def _capture_and_upload_screenshot(page, url: str) -> tuple[str, str]:
    """
    截图并上传到 R2，返回 (截图 URL, 缩略图 URL)
    """
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


async def _extract_feishu_doc_data(page, url: str) -> Dict[str, str]:
    """
    提取飞书文档：标题 & 正文（纯文本，用换行分段）
    """
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title else "飞书文档"

    container = soup.find("div", class_="docx-richtext-container")
    if container:
        content = container.get_text("\n", strip=True)
    else:
        # 兜底：抓取所有 <p>
        paragraphs = soup.find_all("p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs if p)

    return {
        "title": title,
        "description": content[:200] if content else "暂无内容",
        "detail": content,
        "tags": ["feishu"],
        "url": url,
    }


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
@skip_if_visited
async def parse_feishu_doc(url: str) -> Optional[Dict[str, Any]]:
    """
    解析 Feishu DocX：
      1. Playwright 加载页面并截图
      2. BeautifulSoup 提取正文
      3. LLMUtil → chunks & summary
    返回统一结构；失败时返回包含 error 信息的 dict。
    """
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

                # ① 截图
                screenshot_url, thumbnail_url = await _capture_and_upload_screenshot(
                    page, url
                )

                # ② 抽取正文
                doc_data = await _extract_feishu_doc_data(page, url)

                # ③ LLM 处理
                chunks: List[Dict[str, Any]] = _llm.split_and_embed(doc_data["detail"])
                summary: str = _llm.summarize_md(doc_data["detail"])

                return {
                    **doc_data,
                    "screenshot_data": screenshot_url,
                    "screenshot_thumbnail_data": thumbnail_url,
                    "chunks": chunks,
                    "summary": summary,
                }

            except TimeoutError:
                return {
                    "title": "加载超时",
                    "description": "页面加载超时，请稍后重试。",
                    "detail": "",
                    "screenshot_data": "",
                    "screenshot_thumbnail_data": "",
                    "tags": ["feishu", "error"],
                    "url": url,
                }
            finally:
                await page.close()
                await context.close()
                await browser.close()

    except Exception as e:
        logger.exception("飞书解析失败")
        return {
            "title": "解析失败",
            "description": f"发生错误: {str(e)}",
            "detail": "",
            "screenshot_data": "",
            "screenshot_thumbnail_data": "",
            "tags": ["feishu", "error"],
            "url": url,
        }
