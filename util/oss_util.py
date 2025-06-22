import os
import time
import logging
from io import BytesIO
import requests
from datetime import datetime
import random
from PIL import Image
from dotenv import load_dotenv
from botocore.client import Config
import boto3
from util.common_util import CommonUtil

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OSSUtil:
    def __init__(self):
        load_dotenv()
        self.S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL')
        self.S3_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID')
        self.S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY')
        self.S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
        self.S3_CUSTOM_DOMAIN = os.getenv('S3_CUSTOM_DOMAIN')

        # 初始化 S3 客户端
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.S3_ENDPOINT_URL,
            aws_access_key_id=self.S3_ACCESS_KEY_ID,
            aws_secret_access_key=self.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )

    def compress_image_to_webp(self, image_data, quality=85):
        image = Image.open(BytesIO(image_data))
        buffer = BytesIO()
        image.save(buffer, format='WEBP', quality=quality)
        buffer.seek(0)
        return buffer.getvalue()

    def get_default_file_key(self, url, is_thumbnail=False):
        now = datetime.now()
        image_name = CommonUtil.get_name_by_url(url) if url else str(random.randint(1000, 9999))
        if is_thumbnail:
            image_name = f"{image_name}-thumbnail"
        timestamp = int(time.time())
        return f"tools/{now.year}/{now.month}/{now.day}/{image_name}-{timestamp}.png"

    def get_file_url(self, file_key: str) -> str:
        """生成带域名的最终访问链接，优先使用自定义域名"""
        logger.info(f"✅ 当前自定义域名: {self.S3_CUSTOM_DOMAIN}")
        if self.S3_CUSTOM_DOMAIN:
            domain = self.S3_CUSTOM_DOMAIN.replace("https://", "").replace("http://", "").rstrip("/")
            return f"https://{domain}/{file_key}"
        return f"{self.S3_ENDPOINT_URL}/{self.S3_BUCKET_NAME}/{file_key}"

    def upload_file_to_r2(self, file_path, file_key):
        try:
            if file_path.startswith("http"):
                headers = {
                    'accept': 'image/webp,image/apng,*/*',
                    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                }
                image_data = requests.get(file_path, headers=headers).content
            else:
                with open(file_path, 'rb') as f:
                    image_data = f.read()

            compressed = self.compress_image_to_webp(image_data)
            self.s3.upload_fileobj(BytesIO(compressed), self.S3_BUCKET_NAME, file_key)

            logger.info(f"✅ 文件上传成功: {file_key}")
            if os.path.exists(file_path):
                os.remove(file_path)

            return self.get_file_url(file_key)

        except Exception as e:
            logger.error(f"❌ 上传文件失败: {file_path}, 错误: {e}")
            return None

    def generate_thumbnail_image(self, url, original_key):
        try:
            response = self.s3.get_object(Bucket=self.S3_BUCKET_NAME, Key=original_key)
            image = Image.open(BytesIO(response['Body'].read()))

            # 生成缩略图（50%缩放）
            resized = image.resize((image.width // 2, image.height // 2))
            buffer = BytesIO()
            resized.save(buffer, format='PNG')
            buffer.seek(0)

            # 压缩为 WebP 并上传
            compressed = self.compress_image_to_webp(buffer.getvalue())
            thumb_key = self.get_default_file_key(url, is_thumbnail=True)
            self.s3.put_object(Bucket=self.S3_BUCKET_NAME, Key=thumb_key, Body=compressed)

            logger.info(f"🖼️ 缩略图上传成功: {thumb_key}")
            return self.get_file_url(thumb_key)

        except Exception as e:
            logger.error(f"❌ 生成缩略图失败: {e}")
            return None
