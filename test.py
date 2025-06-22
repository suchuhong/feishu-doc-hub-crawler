from parsers.feishu import parse_feishu_doc
import re

# res = parse_feishu_doc("https://axbx9b155gq.feishu.cn/sheets/EJ7KsDqv5h7pH6tRSincSxl5ngd")
# print(res['title'])
# print(res['description'])

# pip install playwright
# playwright install  
# python -m venv .venv
# .venv\Scripts\activate
# pip uninstall pyppeteer -y

# python -m pip install colorlog
# python -m pip install python-json-logger

def is_valid_feishu_link(url: str) -> bool:
    url = url.strip()
    return re.match(r"^https://[\w\-]+\.feishu\.cn/(wiki|docx|sheets)/[A-Za-z0-9]+", url) is not None

test_urls = [
    "https://zw73xyquvv.feishu.cn/wiki/UH5QwtUWtis1gTk4R6rcnWK2nZc",
    " https://waytoagi.feishu.cn/wiki/RJofwtPcci6YMJkzBP2cRFFOnIR ",
    "https://abc.feishu.cn/docx/XxXx1234",
    "https://invalid.feishu.cn/page/123",
]

for url in test_urls:
    print(url, "=>", is_valid_feishu_link(url))