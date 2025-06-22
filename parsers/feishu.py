# parsers/feishu.py

import base64
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError

async def parse_feishu_doc(url: str) -> dict:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(url, timeout=20000)
                await page.wait_for_timeout(5000)  # 防止内容未渲染完

                # 截图 base64 编码
                screenshot = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

                # 获取渲染 HTML
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # 提取标题
                title = soup.title.string.strip() if soup.title else "飞书文档"

                # 提取内容
                content = ""
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
                    "screenshot_data": screenshot_b64,
                    "tags": ["feishu"]
                }

            except TimeoutError:
                return {
                    "title": "加载超时",
                    "description": "页面加载超时，请稍后重试。",
                    "detail": "",
                    "screenshot_data": "",
                    "tags": ["feishu", "error"]
                }
            finally:
                await page.close()
                await context.close()
                await browser.close()

    except Exception as e:
        return {
            "title": "解析失败",
            "description": f"发生错误: {str(e)}",
            "detail": "",
            "screenshot_data": "",
            "tags": ["feishu", "error"]
        }
