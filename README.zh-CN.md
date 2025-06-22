# Feishu Document Hub Crawler

Feishu Document Hub Crawler 是由 [tap4.ai](https://tap4.ai) 开发的开源爬虫，专门设计用于抓取和提取飞书（Lark）文档和知识库内容。它可以将飞书文档转换为使用 LLM 总结的内容摘要。包括强大的文档抓取、数据提取功能，以及文档截图功能。使用 Feishu Document Hub Crawler，您可以轻松提取并处理飞书文档、知识库和表格中的内容。

该项目基于 Python，非常轻量级，易于维护，适合对文档处理和知识管理感兴趣的个人开发者，也适合对 Python 爬虫技术感兴趣的学习者。我们欢迎大家 fork 和 star。

简体中文 | [English](./README.md)

## 特征

- 专门爬取飞书（Lark）文档、知识库和表格
- 获取飞书文档的标题、描述和内容
- 对飞书文档进行截图
- 支持使用 LLM（llama3/chatgpt）处理文档内容并生成 SEO 友好的 Markdown 描述
- 通过关键词发现公开的飞书文档
- 快速配置
- 快速部署

## 快速开始

- [在 Cloudflare 上注册](https://www.cloudflare.com?utm_source=tap4ai)
- 选择 R2 服务并创建一个用于图像存储的存储桶，设置为公共访问（可选：设置自定义域名）并编辑 CORS 策略。
  ![Create-cloudflare-R2](./images/cloudflare-r2.png)
- CORS 策略如下：

```sh
[
  {
    "AllowedOrigins": [
      "*"
    ],
    "AllowedMethods": [
      "GET",
      "POST",
      "PUT",
      "DELETE",
      "HEAD"
    ],
    "AllowedHeaders": [
      "*"
    ]
  }
]
```

- 为 R2 API 创建 R2 API Token，并选择具有对象读写权限的权限。保存您的参数：ENDPOINT_URL、BUCKET_NAME、ACCESS_KEY_ID、SECRET_ACCESS_KEY、CUSTOM_DOMAIN。这些参数将在 feishu-doc-hub 的 .env 文件中配置。
  ![Create-R2-API-Token](./images/Create-R2-API-Token.png)

  ![Cloudflare-R2-Token](./images/Cloudflare-R2-Token.png)

### 在 Zeabur 基于代码模式的部署

在 Zeabur 选择 Fork 后的 Github 仓库部署，并在 Zeabur 配置环境变量，或者手动修改代码仓库的`.env` 文件，环境变量如下：

- `OPENROUTER_API_KEY`: openrouter 的 key，申请[Groq key](https://openrouter.ai/settings/keys)
- `S3_ENDPOINT_URL`: S3 的 endpoint，申请[Cloudflare R2](https://www.cloudflare.com/zh-cn/developer-platform/r2/)
- `S3_BUCKET_NAME`: S3 的 bucket name
- `S3_ACCESS_KEY_ID`: S3 的 access key id
- `S3_SECRET_ACCESS_KEY`: S3 的 secret access key
- `S3_CUSTOM_DOMAIN`: S3 的 custom domain，若有自定义域名，则填入，否则可不填写
- `AUTH_SECRET`: 自定义的对外 REST API 需要的 KEY

**注：爬虫对服务器配置有一定的要求，建议 Zeabur 购买付费服务，优先选择美国节点**

## 本地运行

### 安装

- python3.x 版本

### 设置

#### (1) 克隆此项目

```sh
git clone https://github.com/6677-ai/feishu-doc-hub.git
cd feishu-doc-hub/crawler
```

#### (2) 在 groq 申请 llama3 的 key

[申请 Groq key](https://console.groq.com/keys)

#### (3) 申请 S3 对象存储的信息

- Endpoint
- Accese Key Id
- Secret Access Key
- Bucket Name

#### (4) 设置环境变量

- 修改根目录的 `.env` 文件，修改以下内容，例子如下：

```sh
## LLM Configuration: 大模型相关配置
GROQ_API_KEY=gsk_********

## Object Storage Configuration: 存储相关配置
S3_ENDPOINT_URL=https://*****.r2.cloudflarestorage.com
S3_BUCKET_NAME=tap4ai
S3_ACCESS_KEY_ID=****
S3_SECRET_ACCESS_KEY=****
S3_CUSTOM_DOMAIN=****
AUTH_SECRET=****
```

#### (5) 本地运行

install python 依赖

```sh
pip install -r requirements.txt
```

运行

```sh
python main_api.py
```

运行后则会暴露一个 RestAPI，访问 URL 后缀：/site/crawl

## 如何请求 API

可以使用 curl 发送 Post 请求验证 API 是否可用。
请求参数说明:

- 格式: Json format
- 参数: url (例如: https://example.feishu.cn/wiki/wikcnxxxxxxxxxx)

请求示例如下:

```sh
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer xxxxx" -d '{"url": "https://example.feishu.cn/wiki/wikcnxxxxxxxxxx", "tags": ["document","wiki","knowledge-base"]}' http://127.0.0.1:8040/site/crawl
```

### 发现飞书文档

您还可以使用发现 API 基于关键词查找公开的飞书文档：

```sh
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer xxxxx" -d '{"keyword": "搜索关键词", "max_results": 5}' http://127.0.0.1:8040/site/crawl_discover
```

返回参数:

- 格式: Json
- 参数: data-description: 文档描述
- 参数: data-detail: 文档具体内容
- 参数: data-screenshot_data: 文档截图
- 参数: data-screenshot_thumbnail_data: 文档截图缩略图，0.5 倍分辨率
- 参数: data-title: 文档标题

```sh
{
    "code": 200,
    "data": {
        "description": "从飞书提取的文档描述",
        "detail": "从飞书提取的完整文档内容",
        "links": [{"text": "链接文本", "href": "https://example.com"}],
        "screenshot_data": "https://your-bucket.r2.cloudflarestorage.com/path/to/screenshot.png",
        "screenshot_thumbnail_data": "https://your-bucket.r2.cloudflarestorage.com/path/to/thumbnail.png",
        "tags": ["feishu", "wiki"],
        "title": "文档标题",
        "url": "https://example.feishu.cn/wiki/wikcnxxxxxxxxxx"
    },
    "msg": "success"
}
```

## 常见问题

- 由于飞书可能出现反爬虫，导致爬取失败，需要人工做二次检查
- LLM 处理出来的信息不符合期望，可以尝试自己去优化 prompt 提示词内容
- 爬虫对服务器配置有一定的要求，Zeabur 上使用免费模式很容易出现无法正常运行问题，建议付费

## 相关产品

### TAP4-AI 导航站

全球 AI 工具导航站，搜集全球主流的 AI 工具，目前支持免费提交收录 AI 工具。更多详情，请访问: [Tap4 AI](https://tap4.ai)
