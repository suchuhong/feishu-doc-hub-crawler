# Feishu Document Hub Crawler

Feishu Document Hub Crawler is an open source web crawler built by [tap4.ai](https://tap4.ai), specifically designed to crawl and extract content from Feishu (Lark) documents and wikis. It converts Feishu documents into summarized information with LLM processing capabilities. Includes features for document scraping, data extraction, and webpage screenshots. With Feishu Document Hub Crawler, you can easily extract and process content from Feishu documents, wikis, and sheets.

This project is based on Python, very lightweight, easy to maintain, suitable for individual developers interested in document processing and knowledge management, and also for learners interested in Python crawling techniques. We welcome everyone to fork and star.

English | [简体中文](./README.zh-CN.md)

## Features

- Specialized in crawling Feishu (Lark) documents, wikis, and sheets
- Fetching titles, descriptions, and content from Feishu documents
- Making screenshots of the Feishu documents
- Support for using LLM (llama3/chatgpt) to process document content and generate SEO Friendly Markdown descriptions
- Discovering public Feishu documents through search keywords
- Quick configuration
- Fast deployment

## Quick Start

- [Register on Cloudflare](https://www.cloudflare.com?utm_source=tap4ai&utm_campaign=oss)
- Select R2 Service and create a bucket for image store, set for public access(option: set custom domain) and edit CORS Policy.
  ![Create-cloudflare-R2](./images/cloudflare-r2.png)
- CORS Policy as below:

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

- Create R2 API Tokens for R2 API and select permission with Object Read & Write. Save your own params: ENDPOINT_URL, BUCKET_NAME, ACCESS_KEY_ID, SECRET_ACCESS_KEY, CUSTOM_DOMAIN. The params will config in the .env for feishu-doc-hub crawler.
  ![Create-R2-API-Token](./images/Create-R2-API-Token.png)
  ![Cloudflare-R2-Token](./images/Cloudflare-R2-Token.png)

- [![Register on Zeabur](https://zeabur.com/deployed-on-zeabur-dark.svg)](https://zeabur.com?referralCode=leoli202303&utm_source=leoli202303&utm_campaign=oss)
- Create a new project and service on Zeabur
  **Note: Web scraping requires certain server configurations. It is recommended to purchase paid services from Zeabur and prioritize selecting U.S. nodes.**
- Fork [feishu-doc-hub/crawler](https://github.com/6677-ai/feishu-doc-hub) to your own github and update .env params with your own.

### Deploying in Zeabur based on code mode

Deploying the fork github repository in Zeabur, and configuring environment variables in Zeabur or manually modifying the .env file in the code repository. The environment variables are as follows:

- `OPENROUTER_API_KEY`: Key for openrouter, apply for it [Here](https://openrouter.ai/settings/keys)
- `S3_ENDPOINT_URL`: Endpoint for S3(Recommand Cloudflare R2), apply for [R2](https://www.cloudflare.com/zh-cn/developer-platform/r2/)
- `S3_BUCKET_NAME`: Bucket name for S3(such as Cloudflare R2)
- `S3_ACCESS_KEY_ID`: Access key ID for S3(such as Cloudflare R2)
- `S3_SECRET_ACCESS_KEY`: Secret access key for S3(such as Cloudflare R2)
- `S3_CUSTOM_DOMAIN`: Custom domain for S3(such as Cloudflare R2), if you have a custom domain, fill it in; otherwise, it can be left blank.
- `AUTH_SECRET`: Custom access key for Rest API.

## Runs on local

### Install

- Python 3.x version

### Setup

#### (1) Clone this project

```sh
git clone https://github.com/6677-ai/feishu-doc-hub.git
cd feishu-doc-hub/crawler
```

#### (2) Apply for llama3 key on Groq

[Groq key apply](https://console.groq.com/keys)

#### (3) Apply for S3 object storage information

- Endpoint
- Access Key Id
- Secret Access Key
- Bucket Name

#### (4) Set environment variables

- Modify the `.env` file in the root directory with the following content, example:

```sh
## LLM Configuration: Large model related configuration
GROQ_API_KEY=gsk_********

## Object Storage Configuration: Storage related configuration
S3_ENDPOINT_URL=https://*****.r2.cloudflarestorage.com
S3_BUCKET_NAME=tap4ai
S3_ACCESS_KEY_ID=****
S3_SECRET_ACCESS_KEY=****
S3_CUSTOM_DOMAIN=****
AUTH_SECRET=****
```

#### (5) Run locally

Install Python dependencies

```sh
pip install -r requirements.txt
```

Run

```sh
python main_api.py
```

After running, a RestAPI will be exposed, access URL suffix: /site/crawl

## How to request the API

Use curl to verify the API with POST request.
Request params:

- Format: Json format
- Params: url (such as: https://example.feishu.cn/wiki/wikcnxxxxxxxxxx)
  
Request as below:

```sh
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer xxxxx" -d '{"url": "https://example.feishu.cn/wiki/wikcnxxxxxxxxxx", "tags": ["document","wiki","knowledge-base"]}' http://127.0.0.1:8040/site/crawl
```

### Discovering Feishu Documents

You can also use the discover API to find public Feishu documents based on keywords:

```sh
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer xxxxx" -d '{"keyword": "your search keyword", "max_results": 5}' http://127.0.0.1:8040/site/crawl_discover
```

Response Params:

- Format: Json format
- Params: data-description: Description of document
- Params: data-detail: Detail content of document
- Params: data-screenshot_data: Screenshot of document
- Params: data-screenshot_thumbnail_data: Screenshot thumbnail of document
- Params: data-title: Title of document

```sh
{
    "code": 200,
    "data": {
        "description": "Document description extracted from Feishu",
        "detail": "Full document content extracted from Feishu",
        "links": [{"text": "Link text", "href": "https://example.com"}],
        "screenshot_data": "https://your-bucket.r2.cloudflarestorage.com/path/to/screenshot.png",
        "screenshot_thumbnail_data": "https://your-bucket.r2.cloudflarestorage.com/path/to/thumbnail.png",
        "tags": ["feishu", "wiki"],
        "title": "Document Title",
        "url": "https://example.feishu.cn/wiki/wikcnxxxxxxxxxx"
    },
    "msg": "success"
}
```

## FAQ

- Due to potential anti-scraping measures on Feishu, crawling may fail, and manual secondary checks are required.
- The information processed by the LLM may not meet expectations; you can try optimizing the prompt content yourself.
- Web scraping requires certain server configurations. It is recommended to purchase paid services from Zeabur and prioritize selecting U.S. nodes.

## Related Products

### TAP4-AI-Directory

The Collection for the AI tools all over the world. | Collect free ChatGPT mirrors, alternatives, prompts, other AI tools, etc. For more, please visit: [Tap4 AI](https://tap4.ai/)
