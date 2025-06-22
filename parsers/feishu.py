# parsers/feishu.py

from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
import base64

def parse_feishu_doc(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        try:
            # 1. 页面加载 + 延迟等待
            page.goto(url, timeout=20000)
            page.wait_for_timeout(5000)  # 加长等待时间防止异步渲染缺失

            # 2. 截图为 base64（可选）
            screenshot = page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

            # 3. 提取 HTML 并解析
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # 4. 提取标题
            title = soup.title.string.strip() if soup.title else "飞书文档"

            # 5. 提取正文内容（docx-richtext-container 是标准 class）
            content = ""
            container = soup.find("div", class_="docx-richtext-container")
            if container:
                content = container.get_text("\n", strip=True)
            else:
                # 兼容性回退
                paragraphs = soup.find_all("p")
                content = "\n".join(p.get_text(strip=True) for p in paragraphs if p)

            # 6. 构建返回结构
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
        except Exception as e:
            return {
                "title": "解析失败",
                "description": f"发生错误: {str(e)}",
                "detail": "",
                "screenshot_data": "",
                "tags": ["feishu", "error"]
            }
        finally:
            browser.close()
