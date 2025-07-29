#!/usr/bin/env python3
"""
Token counting utility module
Used to estimate the number of tokens in a text
"""

import re
import logging

class TokenCounter:
    """Token counter"""

    def __init__(self):
        """Initializes the token counter"""
        self.logger = logging.getLogger(__name__)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimates the number of tokens in a text

        Uses a heuristic method for estimation, suitable for mixed Chinese and English text:
        - English words are counted as 1 token
        - Chinese characters are counted as 1 token
        - Punctuation marks are counted as 0.5 tokens
        - Numbers are counted as 0.8 tokens

        Args:
            text: The text to be calculated

        Returns:
            The estimated number of tokens
        """
        if not text:
            return 0

        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))

        # Count English words (consecutive letter combinations)
        english_words = len(re.findall(r'[a-zA-Z]+', text))

        # Count numbers
        numbers = len(re.findall(r'\d+', text))

        # Count punctuation and special characters
        punctuation = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))

        # Calculate the total number of tokens (using heuristic weights)
        total_tokens = (
            chinese_chars * 1.0 +      # Chinese characters
            english_words * 1.0 +      # English words
            numbers * 0.8 +            # Numbers
            punctuation * 0.5          # Punctuation
        )

        # Add some basic overhead (JSON structure, role tags, etc.)
        base_overhead = len(text.split('\n')) * 2  # 2 extra tokens overhead per line

        estimated_tokens = int(total_tokens + base_overhead)

        self.logger.debug(f"Text token estimation: Chinese {chinese_chars}, English {english_words}, "
                         f"Numbers {numbers}, Punctuation {punctuation}, "
                         f"Base overhead {base_overhead}, Total {estimated_tokens}")

        return estimated_tokens

    def estimate_message_tokens(self, message: dict) -> int:
        """
        Estimates the number of tokens in a single message

        Args:
            message: A message dictionary containing role and content fields

        Returns:
            The estimated number of tokens
        """
        role = message.get('role', '')
        content = message.get('content', '')

        # Calculate content tokens
        content_tokens = self.estimate_tokens(content)

        # Add role and structure overhead
        role_tokens = self.estimate_tokens(role)
        structure_overhead = 10  # JSON structure overhead

        total_tokens = content_tokens + role_tokens + structure_overhead

        self.logger.debug(f"Message token estimation: Role '{role}' {role_tokens} tokens, "
                         f"Content {content_tokens} tokens, Structure overhead {structure_overhead} tokens, "
                         f"Total {total_tokens} tokens")

        return total_tokens

    def estimate_messages_tokens(self, messages: list) -> int:
        """
        Estimates the total number of tokens in a list of messages

        Args:
            messages: A list of messages

        Returns:
            The estimated total number of tokens
        """
        total_tokens = 0
        for message in messages:
            total_tokens += self.estimate_message_tokens(message)

        self.logger.debug(f"Message list token estimation: {len(messages)} messages, total {total_tokens} tokens")

        return total_tokens

    def estimate_prompt_tokens(self, prompt: str) -> int:
        """
        Estimates the number of tokens in a complete prompt

        Args:
            prompt: The complete prompt text

        Returns:
            The estimated number of tokens
        """
        tokens = self.estimate_tokens(prompt)
        self.logger.debug(f"Prompt token estimation: {tokens} tokens")
        return tokens
