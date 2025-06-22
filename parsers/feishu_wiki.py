# parsers/feishu_wiki.py

import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError
from util.oss_util import OSSUtil
from util.common_util import CommonUtil

logger = logging.getLogger(__name__)
oss = OSSUtil()

MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

async def parse_feishu_wiki(url: str) -> dict:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent=MODERN_UA,
                locale="zh-CN",
                viewport={"width": 1920, "height": 1080, "deviceScaleFactor": 2},
                java_script_enabled=True
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=20000, wait_until="networkidle")
                await page.wait_for_timeout(4000)

                # 截图 → 保存 → 上传
                screenshot_path = './' + url.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "-") + '.png'
                await page.screenshot(path=screenshot_path, full_page=True)

                image_key = oss.get_default_file_key(url)
                screenshot_url = oss.upload_file_to_r2(screenshot_path, image_key)
                thumbnail_url = oss.generate_thumbnail_image(url, image_key)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string.strip() if soup.title else "飞书 Wiki"

                # 主体内容提取
                main_content = soup.find("div", {"class": "wiki-render-wrapper"})
                if main_content:
                    content = main_content.get_text("\n", strip=True)
                else:
                    content = soup.get_text("\n", strip=True)

                # 提取链接信息
                links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    text = a.get_text(strip=True)
                    if href.startswith("http"):
                        links.append({
                            "text": text or "[无文字链接]",
                            "href": href
                        })

                return {
                    "title": title,
                    "description": content[:200] if content else "暂无内容",
                    "detail": content,
                    "screenshot_data": screenshot_url,
                    "screenshot_thumbnail_data": thumbnail_url,
                    "tags": ["feishu", "wiki"],
                    "links": links,
                    "url": url
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
                    "url": url
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
            "url": url
        }
