import os
import json
import logging
import requests
from dotenv import load_dotenv
from util.common_util import CommonUtil
from typing import List, Dict, Any

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
util = CommonUtil()


class LLMUtil:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv(
            "OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free"
        )
        self.max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", 5000))
        self.referer = os.getenv("OPENROUTER_REFERER", "")
        self.title = os.getenv("OPENROUTER_TITLE", "")
        self.detail_sys_prompt = os.getenv("DETAIL_SYS_PROMPT")
        self.tag_selector_sys_prompt = os.getenv("TAG_SELECTOR_SYS_PROMPT")
        self.language_sys_prompt = os.getenv("LANGUAGE_SYS_PROMPT")
        self.summary_sys_prompt = os.getenv(
            "SUMMARY_SYS_PROMPT",
            "你是一位助理，请用不超过 200 字为下述 Markdown 文本生成摘要：",
        )

    # ------------------------------------------------------------------ #
    # 你原来就有的 3 个业务函数
    # ------------------------------------------------------------------ #
    def process_detail(self, user_prompt: str) -> str | None:
        logger.info("正在处理Detail...")
        return util.detail_handle(self.process_prompt(self.detail_sys_prompt, user_prompt))

    def process_tags(self, user_prompt: str) -> List[str]:
        logger.info("正在处理tags...")
        result = self.process_prompt(self.tag_selector_sys_prompt, user_prompt)
        tags = [t.strip() for t in result.split(",")] if result else []
        logger.info(f"tags处理结果: {tags}")
        return tags

    def process_language(self, language: str, user_prompt: str) -> str:
        logger.info(f"正在处理多语言:{language}, user_prompt:{user_prompt}")
        if "english" in language.lower():
            return user_prompt

        prompt = self.language_sys_prompt.replace("{language}", language)
        result = self.process_prompt(prompt, user_prompt)

        if result and not user_prompt.startswith("#"):
            result = (
                result.replace("### ", "")
                .replace("## ", "")
                .replace("# ", "")
                .replace("**", "")
            )
        logger.info(f"多语言:{language}, 处理结果:{result}")
        return result

    # ------------------------------------------------------------------ #
    # 对 OpenRouter 的通用调用
    # ------------------------------------------------------------------ #
    def process_prompt(self, sys_prompt: str | None, user_prompt: str | None) -> str | None:
        if not sys_prompt:
            logger.info("LLM无需处理，sys_prompt为空")
            return None
        if not user_prompt:
            logger.info("LLM无需处理，user_prompt为空")
            return None

        logger.info("LLM正在处理（OpenRouter）")
        try:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ]
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            if self.referer:
                headers["HTTP-Referer"] = self.referer
            if self.title:
                headers["X-Title"] = self.title

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
            )
            if response.status_code == 200:
                resp_json = response.json()
                content = (
                    resp_json.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                logger.info("LLM返回成功")
                return content
            else:
                logger.error(
                    f"OpenRouter API 请求失败: {response.status_code}, {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"OpenRouter 请求异常: {e}")
            return None

    # ------------------------------------------------------------------ #
    # ★ 新增：切片 + 向量化
    # ------------------------------------------------------------------ #
    def split_and_embed(
        self, markdown_text: str, chunk_size: int = 500
    ) -> List[Dict[str, Any]]:
        """
        把 Markdown 文本按 `chunk_size` 字符切片，并返回:
            [{"text": "...", "embedding": [...]}, ...]
        如果 CommonUtil 提供 `embed_texts(chunks)` 就用真实 embedding，
        否则 embedding 返回空列表占位。
        """
        if not markdown_text:
            return []

        # ① 切片 (如已有更好算法可替换)
        chunks: List[str] = [
            markdown_text[i : i + chunk_size]
            for i in range(0, len(markdown_text), chunk_size)
        ]

        # ② 向量化
        if hasattr(util, "embed_texts"):
            try:
                embeddings = util.embed_texts(chunks)  # type: ignore[attr-defined]
            except Exception as e:
                logger.error(f"embed_texts 调用异常: {e}")
                embeddings = [[] for _ in chunks]
        else:
            embeddings = [[] for _ in chunks]

        return [
            {"text": t, "embedding": emb} for t, emb in zip(chunks, embeddings)
        ]

    # ------------------------------------------------------------------ #
    # ★ 新增：Markdown 摘要
    # ------------------------------------------------------------------ #
    def summarize_md(self, markdown_text: str) -> str:
        """
        调用 LLM 生成 ≤200 字摘要。（可在 .env 里覆盖 SUMMARY_SYS_PROMPT）
        """
        if not markdown_text:
            return ""
        summary = self.process_prompt(self.summary_sys_prompt, markdown_text)
        return summary or ""
