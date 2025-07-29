"""
Simple system test
"""

import unittest
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.table_manager import TableManager
from src.conversation_processor import ConversationProcessor, ChatMessage, ChatRound
from src.prompt_manager import PromptManager

class TestMemorySystem(unittest.TestCase):
    """Memory system test class"""

    def setUp(self):
        """Set up the test environment"""
        self.table_manager = TableManager()
        self.chat_processor = ConversationProcessor()
        self.prompt_handler = PromptManager(self.table_manager)

    def test_table_manager_initialization(self):
        """Test table manager initialization"""
        # Test if all tables are initialized correctly
        info = self.table_manager.get_all_tables_info()
        self.assertEqual(len(info), 6)  # There should be 6 tables

        # Test if each table has the correct columns
        for table_index in range(6):
            self.assertIn(table_index, info)
            self.assertGreaterEqual(info[table_index]["row_count"], 0)

    def test_table_operations(self):
        """Test table operations"""
        # Test inserting a row
        test_data = {0: "Test Character", 1: "Test Trait", 2: "Test Personality"}
        success = self.table_manager.insert_row(1, test_data)
        self.assertTrue(success)

        # Test loading a table
        df = self.table_manager.load_table(1)
        self.assertGreater(len(df), 0)

        # Test updating a row
        update_data = {2: "Updated Personality"}
        success = self.table_manager.update_row(1, 0, update_data)
        self.assertTrue(success)

        # Test deleting a row
        success = self.table_manager.delete_row(1, 0)
        self.assertTrue(success)

    def test_chat_processor(self):
        """Test conversation processor"""
        # Create a test conversation
        test_round = ChatRound(
            round_id=999,
            messages=[
                ChatMessage("user", "Test message 1"),
                ChatMessage("assistant", "Test reply 1")
            ],
            summary="Test summary"
        )

        # Test adding a conversation round
        success = self.chat_processor.add_chat_round(test_round)
        self.assertTrue(success)

        # Test getting a conversation round
        retrieved_round = self.chat_processor.get_chat_round_by_id(999)
        self.assertIsNotNone(retrieved_round)
        self.assertEqual(retrieved_round.round_id, 999)
        self.assertEqual(len(retrieved_round.messages), 2)

    def test_prompt_handler(self):
        """Test prompt handler"""
        # Test generating a prompt
        conversation_text = "[user]: Test conversation\n[assistant]: Test reply"
        prompt = self.prompt_handler.generate_prompt_with_tables(conversation_text)

        # Check if the prompt contains the necessary content
        self.assertIn("dataTable", prompt)
        self.assertIn("Current conversation content", prompt)
        self.assertIn(conversation_text, prompt)

        # Test parsing table operations
        test_response = """
        <tableEdit>
        insertRow(1, {0: "Test Character", 1: "Test Trait"})
        updateRow(1, 0, {2: "Updated Personality"})
        deleteRow(1, 0)
        </tableEdit>
        """

        operations = self.prompt_handler.extract_table_operations(test_response)
        self.assertEqual(len(operations), 3)

        # Check operation types
        operation_types = [op.operation_type for op in operations]
        self.assertIn("insertRow", operation_types)
        self.assertIn("updateRow", operation_types)
        self.assertIn("deleteRow", operation_types)

if __name__ == "__main__":
    unittest.main()