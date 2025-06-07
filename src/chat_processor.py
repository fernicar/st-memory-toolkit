#!/usr/bin/env python3
"""
对话处理模块
负责处理聊天数据的加载、解析和管理
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 导入配置 - 更新为从根目录的config.py导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import get_chat_file_path

@dataclass
class ChatMessage:
    """对话消息数据类"""
    role: str  # 角色：user, assistant, system
    content: str  # 消息内容
    timestamp: Optional[str] = None  # 时间戳
    metadata: Optional[Dict[str, Any]] = None  # 元数据

@dataclass
class ChatRound:
    """对话轮次数据类"""
    round_id: int  # 轮次ID
    messages: List[ChatMessage]  # 消息列表
    summary: Optional[str] = None  # 轮次摘要
    metadata: Optional[Dict[str, Any]] = None  # 元数据

class ChatProcessor:
    """对话处理器类"""

    def __init__(self):
        """初始化对话处理器"""
        self.logger = logging.getLogger(__name__)
        self.chat_file = get_chat_file_path()
        self.chat_data: List[ChatRound] = []

    def load_chat_data(self) -> bool:
        """
        从JSON文件加载对话数据

        Returns:
            加载是否成功
        """
        try:
            with open(self.chat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.chat_data = []

            # 解析对话数据
            if isinstance(data, list):
                # 检查是否是简单的消息列表格式 [{"role": "user", "content": "..."}, ...]
                if data and all(isinstance(item, dict) and "role" in item and "content" in item for item in data):
                    # 简单消息列表格式，转换为单轮对话
                    messages = [self._parse_message(msg_data) for msg_data in data]
                    chat_round = ChatRound(
                        round_id=1,
                        messages=[msg for msg in messages if msg is not None],
                        summary="从简单消息列表加载的对话"
                    )
                    self.chat_data.append(chat_round)
                else:
                    # 数据格式：[{round_id, messages, ...}, ...]
                    for round_data in data:
                        chat_round = self._parse_chat_round(round_data)
                        if chat_round:
                            self.chat_data.append(chat_round)
            elif isinstance(data, dict):
                # 数据格式：{"rounds": [...]} 或 {"messages": [...]}
                if "rounds" in data:
                    for round_data in data["rounds"]:
                        chat_round = self._parse_chat_round(round_data)
                        if chat_round:
                            self.chat_data.append(chat_round)
                elif "messages" in data:
                    # 单轮对话格式
                    chat_round = ChatRound(
                        round_id=1,
                        messages=[self._parse_message(msg) for msg in data["messages"]]
                    )
                    self.chat_data.append(chat_round)

            self.logger.info(f"成功加载 {len(self.chat_data)} 轮对话数据")
            return True

        except FileNotFoundError:
            self.logger.warning(f"对话文件不存在: {self.chat_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"加载对话数据失败: {e}")
            return False

    def load_chat_data_from_file(self, file_path: str) -> bool:
        """
        从指定文件加载对话数据

        Args:
            file_path: 文件路径

        Returns:
            加载是否成功
        """
        original_file = self.chat_file
        self.chat_file = file_path
        result = self.load_chat_data()
        self.chat_file = original_file
        return result

    def _parse_chat_round(self, round_data: Dict[str, Any]) -> Optional[ChatRound]:
        """
        解析单轮对话数据

        Args:
            round_data: 轮次数据字典

        Returns:
            ChatRound对象或None
        """
        try:
            round_id = round_data.get("round_id", round_data.get("id", 0))
            messages_data = round_data.get("messages", [])

            messages = []
            for msg_data in messages_data:
                message = self._parse_message(msg_data)
                if message:
                    messages.append(message)

            return ChatRound(
                round_id=round_id,
                messages=messages,
                summary=round_data.get("summary"),
                metadata=round_data.get("metadata")
            )

        except Exception as e:
            self.logger.error(f"解析对话轮次失败: {e}")
            return None

    def _parse_message(self, msg_data: Dict[str, Any]) -> Optional[ChatMessage]:
        """
        解析单条消息数据

        Args:
            msg_data: 消息数据字典

        Returns:
            ChatMessage对象或None
        """
        try:
            # 支持多种消息格式
            role = msg_data.get("role", msg_data.get("sender", "user"))
            content = msg_data.get("content", msg_data.get("text", ""))

            return ChatMessage(
                role=role,
                content=content,
                timestamp=msg_data.get("timestamp"),
                metadata=msg_data.get("metadata")
            )

        except Exception as e:
            self.logger.error(f"解析消息失败: {e}")
            return None

    def save_chat_data(self) -> bool:
        """
        保存对话数据到JSON文件

        Returns:
            保存是否成功
        """
        try:
            # 转换为可序列化的格式
            data = []
            for chat_round in self.chat_data:
                round_data = {
                    "round_id": chat_round.round_id,
                    "messages": [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.timestamp,
                            "metadata": msg.metadata
                        }
                        for msg in chat_round.messages
                    ],
                    "summary": chat_round.summary,
                    "metadata": chat_round.metadata
                }
                data.append(round_data)

            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"成功保存对话数据到: {self.chat_file}")
            return True

        except Exception as e:
            self.logger.error(f"保存对话数据失败: {e}")
            return False

    def get_chat_rounds(self) -> List[ChatRound]:
        """获取所有对话轮次"""
        return self.chat_data

    def get_chat_round_by_id(self, round_id: int) -> Optional[ChatRound]:
        """
        根据ID获取指定对话轮次

        Args:
            round_id: 轮次ID

        Returns:
            ChatRound对象或None
        """
        for chat_round in self.chat_data:
            if chat_round.round_id == round_id:
                return chat_round
        return None

    def add_chat_round(self, chat_round: ChatRound) -> bool:
        """
        添加新的对话轮次

        Args:
            chat_round: 对话轮次对象

        Returns:
            添加是否成功
        """
        try:
            # 检查是否已存在相同ID的轮次
            existing = self.get_chat_round_by_id(chat_round.round_id)
            if existing:
                self.logger.warning(f"轮次ID {chat_round.round_id} 已存在，将覆盖")
                self.chat_data = [r for r in self.chat_data if r.round_id != chat_round.round_id]

            self.chat_data.append(chat_round)
            self.chat_data.sort(key=lambda x: x.round_id)

            self.logger.info(f"添加对话轮次: {chat_round.round_id}")
            return True

        except Exception as e:
            self.logger.error(f"添加对话轮次失败: {e}")
            return False

    def get_latest_round(self) -> Optional[ChatRound]:
        """获取最新的对话轮次"""
        if not self.chat_data:
            return None
        return max(self.chat_data, key=lambda x: x.round_id)

    def get_round_content_text(self, round_id: int) -> str:
        """
        获取指定轮次的文本内容

        Args:
            round_id: 轮次ID

        Returns:
            格式化的文本内容
        """
        chat_round = self.get_chat_round_by_id(round_id)
        if not chat_round:
            return ""

        content_parts = []
        for msg in chat_round.messages:
            content_parts.append(f"[{msg.role}]: {msg.content}")

        return "\n".join(content_parts)

    def get_all_content_text(self) -> str:
        """获取所有对话内容的文本"""
        content_parts = []
        for chat_round in self.chat_data:
            content_parts.append(f"=== 轮次 {chat_round.round_id} ===")
            content_parts.append(self.get_round_content_text(chat_round.round_id))
            content_parts.append("")

        return "\n".join(content_parts)

    def create_example_chat_file(self):
        """创建示例对话文件"""
        example_data = [
            {
                "round_id": 1,
                "messages": [
                    {
                        "role": "user",
                        "content": "真银铃，你今天感觉怎么样？",
                        "timestamp": "2024-01-01 10:00:00"
                    },
                    {
                        "role": "assistant",
                        "content": "我今天感觉还不错，刚刚在学校的音乐教室练习了一首新歌。你呢？",
                        "timestamp": "2024-01-01 10:01:00"
                    }
                ],
                "summary": "询问真银铃的状态，她提到在音乐教室练歌"
            },
            {
                "round_id": 2,
                "messages": [
                    {
                        "role": "user",
                        "content": "悠悠也在那里吗？我看到她最近很关心你。",
                        "timestamp": "2024-01-01 10:02:00"
                    },
                    {
                        "role": "assistant",
                        "content": "是的，悠悠刚才还帮我调试音响设备。她确实很关心我，我们是很好的朋友。",
                        "timestamp": "2024-01-01 10:03:00"
                    }
                ],
                "summary": "讨论悠悠对真银铃的关心，确认了她们的友好关系"
            }
        ]

        try:
            import os
            os.makedirs(os.path.dirname(self.chat_file), exist_ok=True)

            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(example_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"创建示例对话文件: {self.chat_file}")

        except Exception as e:
            self.logger.error(f"创建示例对话文件失败: {e}")

    def get_message_pairs(self) -> List[List[ChatMessage]]:
        """
        获取用户-助手消息对列表

        Returns:
            消息对列表，每个消息对包含一个user消息和一个assistant消息
        """
        pairs = []

        for chat_round in self.chat_data:
            current_pair = []

            for message in chat_round.messages:
                if message.role == "user":
                    # 如果当前对不为空，说明之前有未完成的对话，先保存
                    if current_pair:
                        pairs.append(current_pair)
                    current_pair = [message]
                elif message.role == "assistant" and current_pair:
                    # 添加assistant响应到当前对
                    current_pair.append(message)
                    pairs.append(current_pair)
                    current_pair = []

            # 处理只有user消息没有assistant响应的情况
            if current_pair:
                pairs.append(current_pair)

        return pairs

    def get_conversation_history_up_to_pair(self, pair_index: int) -> str:
        """
        获取到指定消息对为止的所有历史对话内容

        Args:
            pair_index: 消息对索引

        Returns:
            格式化的历史对话内容
        """
        pairs = self.get_message_pairs()
        history_pairs = pairs[:pair_index]

        conversation_text = ""
        for i, pair in enumerate(history_pairs):
            conversation_text += f"=== 第{i+1}轮对话 ===\n"
            for message in pair:
                conversation_text += f"[{message.role}]: {message.content}\n"
            conversation_text += "\n"

        return conversation_text

    def get_current_pair_content(self, pair_index: int) -> str:
        """
        获取当前消息对的内容

        Args:
            pair_index: 消息对索引

        Returns:
            当前消息对的格式化内容
        """
        pairs = self.get_message_pairs()
        if pair_index >= len(pairs):
            return ""

        current_pair = pairs[pair_index]
        content = f"=== 当前轮对话 ===\n"
        for message in current_pair:
            content += f"[{message.role}]: {message.content}\n"

        return content