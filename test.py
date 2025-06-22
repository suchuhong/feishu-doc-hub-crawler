from parsers.feishu import parse_feishu_doc

res = parse_feishu_doc("https://axbx9b155gq.feishu.cn/sheets/EJ7KsDqv5h7pH6tRSincSxl5ngd")
print(res['title'])
print(res['description'])

# pip install playwright
# playwright install  
# python -m venv .venv
# .venv\Scripts\activate
# pip uninstall pyppeteer -y
