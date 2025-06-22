# parsers/feishu_wiki.py

import base64
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError

async def parse_feishu_wiki(url: str) -> dict:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            try:
                await page.goto(url, timeout=20000)
                await page.wait_for_timeout(4000)

                screenshot = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string.strip() if soup.title else "飞书 Wiki"

                # 主体内容提取
                main_content = soup.find("div", {"class": "wiki-render-wrapper"})
                if main_content:
                    content = main_content.get_text("\n", strip=True)
                else:
                    content = soup.get_text("\n", strip=True)

                # 链接提取
                links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    text = a.get_text(strip=True)
                    # 只提取有效的 http(s) 链接
                    if href.startswith("http"):
                        links.append({
                            "text": text or "[无文字链接]",
                            "href": href
                        })

                return {
                    "title": title,
                    "description": content[:200] if content else "暂无内容",
                    "detail": content,
                    "screenshot_data": screenshot_b64,
                    "tags": ["feishu", "wiki"],
                    "links": links
                }

            except TimeoutError:
                return {
                    "title": "加载超时",
                    "description": "Wiki 页面加载超时。",
                    "detail": "",
                    "screenshot_data": "",
                    "tags": ["feishu", "wiki", "error"],
                    "links": []
                }
            finally:
                await page.close()
                await context.close()
                await browser.close()

    except Exception as e:
        return {
            "title": "Wiki 解析失败",
            "description": f"发生错误: {str(e)}",
            "detail": "",
            "screenshot_data": "",
            "tags": ["feishu", "wiki", "error"],
            "links": []
        }
