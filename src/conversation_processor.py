#!/usr/bin/env python3
"""
Conversation processing module
Responsible for loading, parsing, and managing chat data
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import configuration - updated to import from config.py in the root directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import get_chat_file_path

@dataclass
class ChatMessage:
    """Dataclass for a chat message"""
    role: str  # Role: user, assistant, system
    content: str  # Message content
    timestamp: Optional[str] = None  # Timestamp
    metadata: Optional[Dict[str, Any]] = None  # Metadata

@dataclass
class ChatRound:
    """Dataclass for a conversation round"""
    round_id: int  # Round ID
    messages: List[ChatMessage]  # List of messages
    summary: Optional[str] = None  # Round summary
    metadata: Optional[Dict[str, Any]] = None  # Metadata

class ConversationProcessor:
    """Conversation processor class"""

    def __init__(self):
        """Initializes the conversation processor"""
        self.logger = logging.getLogger(__name__)
        self.chat_file = get_chat_file_path()
        self.chat_data: List[ChatRound] = []

    def load_chat_data(self) -> bool:
        """
        Loads conversation data from a JSON file

        Returns:
            Whether the loading was successful
        """
        try:
            with open(self.chat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.chat_data = []

            # Parse conversation data
            if isinstance(data, list):
                # Check if it's a simple list of messages format [{"role": "user", "content": "..."}, ...]
                if data and all(isinstance(item, dict) and "role" in item and "content" in item for item in data):
                    # Simple message list format, convert to a single conversation round
                    messages = [self._parse_message(msg_data) for msg_data in data]
                    chat_round = ChatRound(
                        round_id=1,
                        messages=[msg for msg in messages if msg is not None],
                        summary="Conversation loaded from a simple message list"
                    )
                    self.chat_data.append(chat_round)
                else:
                    # Data format: [{round_id, messages, ...}, ...]
                    for round_data in data:
                        chat_round = self._parse_chat_round(round_data)
                        if chat_round:
                            self.chat_data.append(chat_round)
            elif isinstance(data, dict):
                # Data format: {"rounds": [...]} or {"messages": [...]}
                if "rounds" in data:
                    for round_data in data["rounds"]:
                        chat_round = self._parse_chat_round(round_data)
                        if chat_round:
                            self.chat_data.append(chat_round)
                elif "messages" in data:
                    # Single conversation round format
                    chat_round = ChatRound(
                        round_id=1,
                        messages=[self._parse_message(msg) for msg in data["messages"]]
                    )
                    self.chat_data.append(chat_round)

            self.logger.info(f"Successfully loaded {len(self.chat_data)} conversation rounds")
            return True

        except FileNotFoundError:
            self.logger.warning(f"Conversation file not found: {self.chat_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to load conversation data: {e}")
            return False

    def load_chat_data_from_file(self, file_path: str) -> bool:
        """
        Loads conversation data from a specified file

        Args:
            file_path: The file path

        Returns:
            Whether the loading was successful
        """
        original_file = self.chat_file
        self.chat_file = file_path
        result = self.load_chat_data()
        self.chat_file = original_file
        return result

    def _parse_chat_round(self, round_data: Dict[str, Any]) -> Optional[ChatRound]:
        """
        Parses a single conversation round data

        Args:
            round_data: The round data dictionary

        Returns:
            A ChatRound object or None
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
            self.logger.error(f"Failed to parse conversation round: {e}")
            return None

    def _parse_message(self, msg_data: Dict[str, Any]) -> Optional[ChatMessage]:
        """
        Parses a single message data

        Args:
            msg_data: The message data dictionary

        Returns:
            A ChatMessage object or None
        """
        try:
            # Support multiple message formats
            role = msg_data.get("role", msg_data.get("sender", "user"))
            content = msg_data.get("content", msg_data.get("text", ""))

            return ChatMessage(
                role=role,
                content=content,
                timestamp=msg_data.get("timestamp"),
                metadata=msg_data.get("metadata")
            )

        except Exception as e:
            self.logger.error(f"Failed to parse message: {e}")
            return None

    def save_chat_data(self) -> bool:
        """
        Saves conversation data to a JSON file

        Returns:
            Whether the saving was successful
        """
        try:
            # Convert to a serializable format
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

            self.logger.info(f"Successfully saved conversation data to: {self.chat_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save conversation data: {e}")
            return False

    def get_chat_rounds(self) -> List[ChatRound]:
        """Gets all conversation rounds"""
        return self.chat_data

    def get_chat_round_by_id(self, round_id: int) -> Optional[ChatRound]:
        """
        Gets a specific conversation round by ID

        Args:
            round_id: The round ID

        Returns:
            A ChatRound object or None
        """
        for chat_round in self.chat_data:
            if chat_round.round_id == round_id:
                return chat_round
        return None

    def add_chat_round(self, chat_round: ChatRound) -> bool:
        """
        Adds a new conversation round

        Args:
            chat_round: The conversation round object

        Returns:
            Whether the addition was successful
        """
        try:
            # Check if a round with the same ID already exists
            existing = self.get_chat_round_by_id(chat_round.round_id)
            if existing:
                self.logger.warning(f"Round ID {chat_round.round_id} already exists and will be overwritten")
                self.chat_data = [r for r in self.chat_data if r.round_id != chat_round.round_id]

            self.chat_data.append(chat_round)
            self.chat_data.sort(key=lambda x: x.round_id)

            self.logger.info(f"Added conversation round: {chat_round.round_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add conversation round: {e}")
            return False

    def get_latest_round(self) -> Optional[ChatRound]:
        """Gets the latest conversation round"""
        if not self.chat_data:
            return None
        return max(self.chat_data, key=lambda x: x.round_id)

    def get_round_content_text(self, round_id: int) -> str:
        """
        Gets the text content of a specific round

        Args:
            round_id: The round ID

        Returns:
            The formatted text content
        """
        chat_round = self.get_chat_round_by_id(round_id)
        if not chat_round:
            return ""

        content_parts = []
        for msg in chat_round.messages:
            content_parts.append(f"[{msg.role}]: {msg.content}")

        return "\n".join(content_parts)

    def get_all_content_text(self) -> str:
        """Gets the text content of all conversations"""
        content_parts = []
        for chat_round in self.chat_data:
            content_parts.append(f"=== Round {chat_round.round_id} ===")
            content_parts.append(self.get_round_content_text(chat_round.round_id))
            content_parts.append("")

        return "\n".join(content_parts)

    def create_example_chat_file(self):
        """Creates an example conversation file"""
        example_data = [
            {
                "round_id": 1,
                "messages": [
                    {
                        "role": "user",
                        "content": "How are you feeling today?",
                        "timestamp": "2024-01-01 10:00:00"
                    },
                    {
                        "role": "assistant",
                        "content": "I'm feeling pretty good, I just practiced a new song in the school's music room. How about you?",
                        "timestamp": "2024-01-01 10:01:00"
                    }
                ],
                "summary": "Asked about the assistant's status, they mentioned practicing a song in the music room"
            },
            {
                "round_id": 2,
                "messages": [
                    {
                        "role": "user",
                        "content": "Is Yoyo there too? I saw she's been very concerned about you lately.",
                        "timestamp": "2024-01-01 10:02:00"
                    },
                    {
                        "role": "assistant",
                        "content": "Yes, Yoyo just helped me adjust the audio equipment. She is indeed very concerned about me, we are good friends.",
                        "timestamp": "2024-01-01 10:03:00"
                    }
                ],
                "summary": "Discussed Yoyo's concern for the assistant, confirming their friendly relationship"
            }
        ]

        try:
            import os
            os.makedirs(os.path.dirname(self.chat_file), exist_ok=True)

            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(example_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Created example conversation file: {self.chat_file}")

        except Exception as e:
            self.logger.error(f"Failed to create example conversation file: {e}")

    def get_message_pairs(self) -> List[List[ChatMessage]]:
        """
        Gets a list of user-assistant message pairs

        Returns:
            A list of message pairs, each containing a user message and an assistant message
        """
        pairs = []

        for chat_round in self.chat_data:
            current_pair = []

            for message in chat_round.messages:
                if message.role == "user":
                    # If the current pair is not empty, it means there was an unfinished conversation, so save it first
                    if current_pair:
                        pairs.append(current_pair)
                    current_pair = [message]
                elif message.role == "assistant" and current_pair:
                    # Add the assistant's response to the current pair
                    current_pair.append(message)
                    pairs.append(current_pair)
                    current_pair = []

            # Handle cases where there is only a user message without an assistant response
            if current_pair:
                pairs.append(current_pair)

        return pairs

    def get_conversation_history_up_to_pair(self, pair_index: int) -> str:
        """
        Gets all historical conversation content up to a specified message pair

        Args:
            pair_index: The message pair index

        Returns:
            The formatted historical conversation content
        """
        pairs = self.get_message_pairs()
        history_pairs = pairs[:pair_index]

        conversation_text = ""
        for i, pair in enumerate(history_pairs):
            conversation_text += f"=== Round {i+1} ===\n"
            for message in pair:
                conversation_text += f"[{message.role}]: {message.content}\n"
            conversation_text += "\n"

        return conversation_text

    def get_current_pair_content(self, pair_index: int) -> str:
        """
        Gets the content of the current message pair

        Args:
            pair_index: The message pair index

        Returns:
            The formatted content of the current message pair
        """
        pairs = self.get_message_pairs()
        if pair_index >= len(pairs):
            return ""

        current_pair = pairs[pair_index]
        content = f"=== Current Round ===\n"
        for message in current_pair:
            content += f"[{message.role}]: {message.content}\n"

        return content