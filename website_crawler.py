# websit_crawler.py
import logging
import time
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from util.common_util import CommonUtil
from util.llm_util import LLMUtil
from util.oss_util import OSSUtil

llm = LLMUtil()
oss = OSSUtil()
logger = logging.getLogger(__name__)

MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

class WebsitCrawler:
    def __init__(self):
        pass

    async def scrape_website(self, url, tags=None, languages=None):
        start_time = time.time()
        logger.info("正在处理：" + url)

        if not url.startswith("http"):
            url = "https://" + url

        try:
            async with async_playwright() as p:
                browser, context, page = await self._init_browser(p)
                try:
                    await self._navigate_page(page, url)
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    title, description = self._extract_title_description(soup)
                    name = CommonUtil.get_name_by_url(url)
                    content = soup.get_text()

                    screenshot_path = self._build_screenshot_path(url)
                    await page.screenshot(path=screenshot_path, full_page=True)
                    image_key = oss.get_default_file_key(url)
                    screenshot_key = oss.upload_file_to_r2(screenshot_path, image_key)
                    thumbnail_key = oss.generate_thumbnail_image(url, image_key)

                    detail = llm.process_detail(content)
                    processed_tags = self._generate_tags(tags, detail)
                    processed_languages = self._generate_languages(languages, title, description, detail, url)

                    return {
                        "name": name,
                        "url": url,
                        "title": title,
                        "description": description,
                        "detail": detail,
                        "screenshot_data": self.normalize_url(screenshot_key),
                        "screenshot_thumbnail_data": self.normalize_url(thumbnail_key),
                        "tags": processed_tags,
                        "languages": processed_languages
                    }

                finally:
                    await page.close()
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"处理 {url} 站点异常，错误信息: {e}")
            return None
        finally:
            logger.info(f"处理 {url} 用时：{int(time.time() - start_time)} 秒")

    async def _init_browser(self, playwright):
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=MODERN_UA,
            locale="zh-CN",
            viewport={"width": 1920, "height": 1080, "deviceScaleFactor": 2},
            java_script_enabled=True
        )
        page = await context.new_page()
        return browser, context, page

    async def _navigate_page(self, page, url):
        try:
            await page.goto(url, timeout=60000, wait_until="networkidle")
        except Exception as e:
            logger.warning(f"页面加载超时：{e}，继续后续处理")
        await page.wait_for_timeout(1000)

    def _extract_title_description(self, soup):
        title = soup.title.string.strip() if soup.title else ""
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = meta.get("content", "").strip() if meta else ""
        return title, description

    def _build_screenshot_path(self, url):
        return './' + url.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "-") + '.png'

    def _generate_tags(self, tags, detail):
        if tags and detail:
            return llm.process_tags(f"tag_list is: {','.join(tags)}. content is: {detail}")
        return None

    def _generate_languages(self, languages, title, description, detail, url):
        if not languages:
            return []
        result = []
        for lang in languages:
            logger.info(f"{url} 正在生成多语言版本：{lang}")
            result.append({
                "language": lang,
                "title": llm.process_language(lang, title),
                "description": llm.process_language(lang, description),
                "detail": llm.process_language(lang, detail)
            })
        return result

    def normalize_url(self, url: str) -> str:
        return url.replace("https://https://", "https://").replace("http://http://", "http://")
