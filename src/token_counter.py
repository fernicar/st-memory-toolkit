#!/usr/bin/env python3
"""
Token计算工具模块
用于估算文本的token数量
"""

import re
import logging

class TokenCounter:
    """Token计算器"""

    def __init__(self):
        """初始化token计算器"""
        self.logger = logging.getLogger(__name__)

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        使用启发式方法估算，适用于中英文混合文本：
        - 英文单词按1个token计算
        - 中文字符按1个token计算
        - 标点符号按0.5个token计算
        - 数字按0.8个token计算

        Args:
            text: 要计算的文本

        Returns:
            估算的token数量
        """
        if not text:
            return 0

        # 统计中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))

        # 统计英文单词（连续的字母组合）
        english_words = len(re.findall(r'[a-zA-Z]+', text))

        # 统计数字
        numbers = len(re.findall(r'\d+', text))

        # 统计标点符号和特殊字符
        punctuation = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))

        # 计算总token数（使用启发式权重）
        total_tokens = (
            chinese_chars * 1.0 +      # 中文字符
            english_words * 1.0 +      # 英文单词
            numbers * 0.8 +            # 数字
            punctuation * 0.5          # 标点符号
        )

        # 加上一些基础开销（JSON结构、角色标签等）
        base_overhead = len(text.split('\n')) * 2  # 每行额外2个token开销

        estimated_tokens = int(total_tokens + base_overhead)

        self.logger.debug(f"文本token估算: 中文{chinese_chars}, 英文{english_words}, "
                         f"数字{numbers}, 标点{punctuation}, "
                         f"基础开销{base_overhead}, 总计{estimated_tokens}")

        return estimated_tokens

    def estimate_message_tokens(self, message: dict) -> int:
        """
        估算单条消息的token数量

        Args:
            message: 消息字典，包含role和content字段

        Returns:
            估算的token数量
        """
        role = message.get('role', '')
        content = message.get('content', '')

        # 计算内容token
        content_tokens = self.estimate_tokens(content)

        # 加上角色和结构开销
        role_tokens = self.estimate_tokens(role)
        structure_overhead = 10  # JSON结构开销

        total_tokens = content_tokens + role_tokens + structure_overhead

        self.logger.debug(f"消息token估算: 角色'{role}' {role_tokens}token, "
                         f"内容 {content_tokens}token, 结构开销 {structure_overhead}token, "
                         f"总计 {total_tokens}token")

        return total_tokens

    def estimate_messages_tokens(self, messages: list) -> int:
        """
        估算消息列表的总token数量

        Args:
            messages: 消息列表

        Returns:
            估算的总token数量
        """
        total_tokens = 0
        for message in messages:
            total_tokens += self.estimate_message_tokens(message)

        self.logger.debug(f"消息列表token估算: {len(messages)}条消息，总计{total_tokens}token")

        return total_tokens

    def estimate_prompt_tokens(self, prompt: str) -> int:
        """
        估算完整提示词的token数量

        Args:
            prompt: 完整的提示词文本

        Returns:
            估算的token数量
        """
        tokens = self.estimate_tokens(prompt)
        self.logger.debug(f"提示词token估算: {tokens}token")
        return tokens
