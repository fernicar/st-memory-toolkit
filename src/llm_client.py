#!/usr/bin/env python3
"""
LLM Client Module
Handles interaction with external LLM APIs
"""

import logging
import os
import sys
import time
from typing import Optional

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEYS, GEMINI_MODEL

try:
    from google import genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiClient:
    """Gemini API Client"""

    def __init__(self):
        """Initializes the Gemini client"""
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.model = GEMINI_MODEL

        # API key rotation related
        self.api_keys = GEMINI_API_KEYS if GEMINI_API_KEYS else []
        self.current_key_index = 0  # Index of the currently used API key
        self.api_key = self.api_keys[0] if self.api_keys else None

        if not GENAI_AVAILABLE:
            self.logger.error("Google Gen AI library not installed, please run: pip install google-genai")
            return

        if not self.api_keys:
            self.logger.error("GEMINI_API_KEYS not set")
            return

        try:
            # Use the new Google Gen AI SDK
            self.client = genai.Client(api_key=self.api_key)
            self.logger.info(f"Gemini client initialized successfully, {len(self.api_keys)} API keys available")
        except Exception as e:
            self.logger.error(f"Gemini client initialization failed: {e}")

    def _rotate_api_key(self):
        """Rotates to the next API key"""
        if len(self.api_keys) <= 1:
            self.logger.debug("Only one or no API key, no rotation needed")
            return  # Only one or no API key, no rotation needed

        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.api_key = self.api_keys[self.current_key_index]

        try:
            # Create a new client instance
            self.client = genai.Client(api_key=self.api_key)
            self.logger.info(f"🔄 API key rotated: #{old_index + 1} → #{self.current_key_index + 1} ({self.api_key[:10]}...)")
        except Exception as e:
            self.logger.error(f"Failed to rotate API key: {e}")

    def _get_current_api_key_info(self) -> str:
        """Gets information about the current API key (for logging)"""
        if not self.api_keys:
            return "No API key"
        return f"#{self.current_key_index + 1}/{len(self.api_keys)} ({self.api_key[:10]}...)"

    def generate_content(self, prompt: str, max_retries: int = 10) -> Optional[str]:
        """
        Calls the Gemini API to generate content

        Args:
            prompt: The input prompt
            max_retries: The maximum number of retries

        Returns:
            The generated content, or None on failure
        """
        if not self.client:
            self.logger.error("Gemini client not properly initialized")
            return None

        for attempt in range(max_retries):
            try:
                current_key_info = self._get_current_api_key_info()
                self.logger.info(f"Calling Gemini API (attempt {attempt + 1}/{max_retries}) - using API key: {current_key_info}")

                # Before sending the prompt, add single quotes around all \n
                # prompt = prompt.replace('\n', "\'\n\'")
                # prompt = "'".join(c + "'" for c in prompt)
                prompt = prompt.replace('\n', "\'\n\'")

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )

                # Check if the response is valid
                self.logger.info(f"Received response object, type: {type(response)}")

                # Check if it was blocked
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    feedback = response.prompt_feedback
                    if hasattr(feedback, 'block_reason') and feedback.block_reason:
                        self.logger.error(f"Request blocked, reason: {feedback.block_reason}")
                        if hasattr(feedback, 'block_reason_message') and feedback.block_reason_message:
                            self.logger.error(f"Block reason details: {feedback.block_reason_message}")
                        # Rotate API key regardless of the result
                        self._rotate_api_key()
                        return None

                # Check if candidates are empty
                if hasattr(response, 'candidates') and response.candidates is None:
                    self.logger.error("Response candidates are empty, content may be filtered")
                    # Rotate API key regardless of the result
                    self._rotate_api_key()
                    return None

                # Try different ways to get the text content
                result = None

                # Method 1: Use the built-in text attribute (this should be the standard way)
                try:
                    if hasattr(response, 'text'):
                        result = response.text
                        if result:
                            self.logger.info(f"Successfully got content via response.text")
                        else:
                            self.logger.info(f"response.text exists but is empty")
                except Exception as e:
                    self.logger.warning(f"Error getting response.text: {e}")

                # Method 2: Get from candidates
                if not result and hasattr(response, 'candidates') and response.candidates:
                    try:
                        self.logger.info(f"Trying to get content from candidates, number of candidates: {len(response.candidates)}")
                        candidate = response.candidates[0]

                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content

                            if hasattr(content, 'parts') and content.parts:
                                part = content.parts[0]

                                if hasattr(part, 'text') and part.text:
                                    result = part.text
                                    self.logger.info(f"Successfully got content via candidates.content.parts.text")
                    except Exception as e:
                        self.logger.warning(f"Error getting content from candidates: {e}")

                # Rotate API key regardless of the result
                self._rotate_api_key()

                if result:
                    self.logger.info(f"Finally got content successfully, length: {len(result)}")
                    return result
                else:
                    self.logger.error(f"Could not get any text content from the response")
                    # If candidates exist but are empty, it might be a content safety filtering issue
                    if hasattr(response, 'candidates') and response.candidates is None:
                        self.logger.error("Content may have violated Gemini's safety policy, please check the input content")
                    return None

            except Exception as e:
                self.logger.error(f"Gemini API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                # Rotate API key regardless of the result
                self._rotate_api_key()

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    self.logger.error("Maximum number of retries reached, giving up")

        return None

    def is_available(self) -> bool:
        """Checks if the client is available"""
        return self.client is not None and GENAI_AVAILABLE

    def test_connection(self) -> bool:
        """Tests the API connection"""
        try:
            result = self.generate_content("Test connection")
            return result is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
