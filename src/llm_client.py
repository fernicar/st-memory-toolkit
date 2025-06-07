#!/usr/bin/env python3
"""
大语言模型客户端模块
负责与外部LLM API进行交互
"""

import logging
import os
import sys
import time
from typing import Optional

# 导入配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEYS, GEMINI_MODEL

try:
    from google import genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiClient:
    """Gemini API客户端"""

    def __init__(self):
        """初始化Gemini客户端"""
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.model = GEMINI_MODEL

        # API key轮换相关
        self.api_keys = GEMINI_API_KEYS if GEMINI_API_KEYS else []
        self.current_key_index = 0  # 当前使用的API key索引
        self.api_key = self.api_keys[0] if self.api_keys else None

        if not GENAI_AVAILABLE:
            self.logger.error("Google Gen AI库未安装，请运行: pip install google-genai")
            return

        if not self.api_keys:
            self.logger.error("未设置GEMINI_API_KEYS")
            return

        try:
            # 使用新的Google Gen AI SDK
            self.client = genai.Client(api_key=self.api_key)
            self.logger.info(f"Gemini客户端初始化成功，共有{len(self.api_keys)}个API key可用")
        except Exception as e:
            self.logger.error(f"Gemini客户端初始化失败: {e}")

    def _rotate_api_key(self):
        """轮换到下一个API key"""
        if len(self.api_keys) <= 1:
            self.logger.debug("只有一个或没有API key，无需轮换")
            return  # 只有一个或没有API key，无需轮换

        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.api_key = self.api_keys[self.current_key_index]

        try:
            # 创建新的客户端实例
            self.client = genai.Client(api_key=self.api_key)
            self.logger.info(f"🔄 API key轮换: #{old_index + 1} → #{self.current_key_index + 1} ({self.api_key[:10]}...)")
        except Exception as e:
            self.logger.error(f"轮换API key失败: {e}")

    def _get_current_api_key_info(self) -> str:
        """获取当前API key的信息（用于日志）"""
        if not self.api_keys:
            return "无API key"
        return f"#{self.current_key_index + 1}/{len(self.api_keys)} ({self.api_key[:10]}...)"

    def generate_content(self, prompt: str, max_retries: int = 10) -> Optional[str]:
        """
        调用Gemini API生成内容

        Args:
            prompt: 输入提示词
            max_retries: 最大重试次数

        Returns:
            生成的内容，失败时返回None
        """
        if not self.client:
            self.logger.error("Gemini客户端未正确初始化")
            return None

        for attempt in range(max_retries):
            try:
                current_key_info = self._get_current_api_key_info()
                self.logger.info(f"调用Gemini API (尝试 {attempt + 1}/{max_retries}) - 使用API key: {current_key_info}")

                # 在发送prompt之前，将所有\n前后加上单引号
                # prompt = prompt.replace('\n', "\'\n\'")
                # prompt = "'".join(c + "'" for c in prompt)
                prompt = prompt.replace('\n', "\'\n\'")

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )

                # 检查响应是否有效
                self.logger.info(f"收到响应对象，类型: {type(response)}")

                # 检查是否被阻止
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    feedback = response.prompt_feedback
                    if hasattr(feedback, 'block_reason') and feedback.block_reason:
                        self.logger.error(f"请求被阻止，原因: {feedback.block_reason}")
                        if hasattr(feedback, 'block_reason_message') and feedback.block_reason_message:
                            self.logger.error(f"阻止原因详情: {feedback.block_reason_message}")
                        # 不管什么结果，都换API key
                        self._rotate_api_key()
                        return None

                # 检查candidates是否为空
                if hasattr(response, 'candidates') and response.candidates is None:
                    self.logger.error("响应的candidates为空，可能内容被过滤")
                    # 不管什么结果，都换API key
                    self._rotate_api_key()
                    return None

                # 尝试不同的方式获取文本内容
                result = None

                # 方式1: 使用内置的text属性 (这应该是标准方式)
                try:
                    if hasattr(response, 'text'):
                        result = response.text
                        if result:
                            self.logger.info(f"通过response.text获取内容成功")
                        else:
                            self.logger.info(f"response.text存在但为空")
                except Exception as e:
                    self.logger.warning(f"获取response.text时出错: {e}")

                # 方式2: 通过candidates获取
                if not result and hasattr(response, 'candidates') and response.candidates:
                    try:
                        self.logger.info(f"尝试通过candidates获取内容，candidates数量: {len(response.candidates)}")
                        candidate = response.candidates[0]

                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content

                            if hasattr(content, 'parts') and content.parts:
                                part = content.parts[0]

                                if hasattr(part, 'text') and part.text:
                                    result = part.text
                                    self.logger.info(f"通过candidates.content.parts.text获取内容成功")
                    except Exception as e:
                        self.logger.warning(f"通过candidates获取内容时出错: {e}")

                # 不管什么结果，都换API key
                self._rotate_api_key()

                if result:
                    self.logger.info(f"最终获取内容成功，长度: {len(result)}")
                    return result
                else:
                    self.logger.error(f"无法从响应中获取任何文本内容")
                    # 如果有candidates但为空，可能是内容安全过滤问题
                    if hasattr(response, 'candidates') and response.candidates is None:
                        self.logger.error("内容可能违反了Gemini的安全策略，请检查输入内容")
                    return None

            except Exception as e:
                self.logger.error(f"Gemini API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                # 不管什么结果，都换API key
                self._rotate_api_key()

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error("达到最大重试次数，放弃调用")

        return None

    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return self.client is not None and GENAI_AVAILABLE

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            result = self.generate_content("测试连接")
            return result is not None
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False
