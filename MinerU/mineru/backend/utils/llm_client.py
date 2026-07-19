"""OpenAI-compatible LLM client for image description."""
import base64
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    max_tokens: int = 1500
    temperature: float = 0.3
    system_prompt: str = ""
    user_prompt: str = "请描述这张图片的内容。"


class ImageDescriber:
    """调用 OpenAI 兼容 API 描述图片内容。"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def describe(self, image_path: str) -> Optional[str]:
        """发送图片到 LLM 获取描述，失败返回 None。"""
        image_b64 = self._encode_image(image_path)

        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.config.user_prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  [LLM] 图片描述失败: {e}")
            return None
