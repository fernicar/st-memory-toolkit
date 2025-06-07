"""
简单的系统测试
"""

import unittest
import os
import sys

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.table_manager import TableManager
from src.chat_processor import ChatProcessor, ChatMessage, ChatRound
from src.prompt_handler import PromptHandler

class TestMemorySystem(unittest.TestCase):
    """内存系统测试类"""

    def setUp(self):
        """设置测试环境"""
        self.table_manager = TableManager()
        self.chat_processor = ChatProcessor()
        self.prompt_handler = PromptHandler(self.table_manager)

    def test_table_manager_initialization(self):
        """测试表格管理器初始化"""
        # 测试所有表格是否正确初始化
        info = self.table_manager.get_all_tables_info()
        self.assertEqual(len(info), 6)  # 应该有6个表格

        # 测试每个表格都有正确的列
        for table_index in range(6):
            self.assertIn(table_index, info)
            self.assertGreaterEqual(info[table_index]["row_count"], 0)

    def test_table_operations(self):
        """测试表格操作"""
        # 测试插入行
        test_data = {0: "测试角色", 1: "测试特征", 2: "测试性格"}
        success = self.table_manager.insert_row(1, test_data)
        self.assertTrue(success)

        # 测试加载表格
        df = self.table_manager.load_table(1)
        self.assertGreater(len(df), 0)

        # 测试更新行
        update_data = {2: "更新的性格"}
        success = self.table_manager.update_row(1, 0, update_data)
        self.assertTrue(success)

        # 测试删除行
        success = self.table_manager.delete_row(1, 0)
        self.assertTrue(success)

    def test_chat_processor(self):
        """测试对话处理器"""
        # 创建测试对话
        test_round = ChatRound(
            round_id=999,
            messages=[
                ChatMessage("user", "测试消息1"),
                ChatMessage("assistant", "测试回复1")
            ],
            summary="测试摘要"
        )

        # 测试添加对话轮次
        success = self.chat_processor.add_chat_round(test_round)
        self.assertTrue(success)

        # 测试获取对话轮次
        retrieved_round = self.chat_processor.get_chat_round_by_id(999)
        self.assertIsNotNone(retrieved_round)
        self.assertEqual(retrieved_round.round_id, 999)
        self.assertEqual(len(retrieved_round.messages), 2)

    def test_prompt_handler(self):
        """测试提示词处理器"""
        # 测试生成提示词
        conversation_text = "[user]: 测试对话\n[assistant]: 测试回复"
        prompt = self.prompt_handler.generate_prompt_with_tables(conversation_text)

        # 检查提示词是否包含必要内容
        self.assertIn("dataTable", prompt)
        self.assertIn("当前对话内容", prompt)
        self.assertIn(conversation_text, prompt)

        # 测试解析表格操作
        test_response = """
        <tableEdit>
        insertRow(1, {0: "测试角色", 1: "测试特征"})
        updateRow(1, 0, {2: "更新性格"})
        deleteRow(1, 0)
        </tableEdit>
        """

        operations = self.prompt_handler.extract_table_operations(test_response)
        self.assertEqual(len(operations), 3)

        # 检查操作类型
        operation_types = [op.operation_type for op in operations]
        self.assertIn("insertRow", operation_types)
        self.assertIn("updateRow", operation_types)
        self.assertIn("deleteRow", operation_types)

if __name__ == "__main__":
    unittest.main()