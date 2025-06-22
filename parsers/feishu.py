# parsers/feishu.py

import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError
from util.oss_util import OSSUtil

logger = logging.getLogger(__name__)
oss = OSSUtil()

MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

async def parse_feishu_doc(url: str) -> dict:
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
                await page.wait_for_timeout(4000)  # 等待异步内容加载

                # 截图 → 保存 → 上传 OSS
                screenshot_path = './' + url.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "-") + '.png'
                await page.screenshot(path=screenshot_path, full_page=True)

                image_key = oss.get_default_file_key(url)
                screenshot_url = oss.upload_file_to_r2(screenshot_path, image_key)
                thumbnail_url = oss.generate_thumbnail_image(url, image_key)

                # 提取内容
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string.strip() if soup.title else "飞书文档"

                container = soup.find("div", class_="docx-richtext-container")
                if container:
                    content = container.get_text("\n", strip=True)
                else:
                    paragraphs = soup.find_all("p")
                    content = "\n".join(p.get_text(strip=True) for p in paragraphs if p)

                return {
                    "title": title,
                    "description": content[:200] if content else "暂无内容",
                    "detail": content,
                    "screenshot_data": screenshot_url,
                    "screenshot_thumbnail_data": thumbnail_url,
                    "tags": ["feishu"],
                    "url": url
                }

            except TimeoutError:
                return {
                    "title": "加载超时",
                    "description": "页面加载超时，请稍后重试。",
                    "detail": "",
                    "screenshot_data": "",
                    "screenshot_thumbnail_data": "",
                    "tags": ["feishu", "error"],
                    "url": url
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
            "url": url
        }
