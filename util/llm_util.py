import os
import json
import logging
import requests
from dotenv import load_dotenv
from util.common_util import CommonUtil

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
util = CommonUtil()

class LLMUtil:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat-v3-0324:free')
        self.max_tokens = int(os.getenv('OPENROUTER_MAX_TOKENS', 5000))
        self.referer = os.getenv('OPENROUTER_REFERER', '')
        self.title = os.getenv('OPENROUTER_TITLE', '')
        self.detail_sys_prompt = os.getenv('DETAIL_SYS_PROMPT')
        self.tag_selector_sys_prompt = os.getenv('TAG_SELECTOR_SYS_PROMPT')
        self.language_sys_prompt = os.getenv('LANGUAGE_SYS_PROMPT')

    def process_detail(self, user_prompt):
        logger.info("正在处理Detail...")
        return util.detail_handle(self.process_prompt(self.detail_sys_prompt, user_prompt))

    def process_tags(self, user_prompt):
        logger.info("正在处理tags...")
        result = self.process_prompt(self.tag_selector_sys_prompt, user_prompt)
        if result:
            tags = [t.strip() for t in result.split(',')]
        else:
            tags = []
        logger.info(f"tags处理结果: {tags}")
        return tags

    def process_language(self, language, user_prompt):
        logger.info(f"正在处理多语言:{language}, user_prompt:{user_prompt}")
        if 'english' in language.lower():
            return user_prompt

        prompt = self.language_sys_prompt.replace("{language}", language)
        result = self.process_prompt(prompt, user_prompt)

        if result and not user_prompt.startswith("#"):
            result = result.replace("### ", "").replace("## ", "").replace("# ", "").replace("**", "")
        logger.info(f"多语言:{language}, 处理结果:{result}")
        return result

    def process_prompt(self, sys_prompt, user_prompt):
        if not sys_prompt:
            logger.info(f"LLM无需处理，sys_prompt为空")
            return None
        if not user_prompt:
            logger.info(f"LLM无需处理，user_prompt为空")
            return None

        logger.info("LLM正在处理（OpenRouter）")
        try:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ]
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            if self.referer:
                headers["HTTP-Referer"] = self.referer
            if self.title:
                headers["X-Title"] = self.title

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload)
            )
            if response.status_code == 200:
                resp_json = response.json()
                content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info("LLM返回成功")
                return content
            else:
                logger.error(f"OpenRouter API 请求失败: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            logger.error(f"OpenRouter 请求异常: {e}")
            return None
