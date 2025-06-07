#!/usr/bin/env python3
"""
提示词处理模块
负责生成包含表格信息的提示词和解析LLM响应
"""

import re
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompt import MEMORY_TABLE_PROMPT, MEMORY_TABLE_PROMPT_INTEGRATION, BYPASSING_CONTENT_FILTERS_PROMPT, END_PROMPT, BYPASSING_CONTENT_FILTERS_PROMPT_MODEL  # 从prompt.py导入系统提示词和绕过过滤器提示词
from config import MAX_CONTEXT_LENGTH, BYPASS_ENHANCEMENT  # 导入最大上下文长度配置
from src.table_manager import TableManager
from src.table_schemas import TABLE_SCHEMAS

# 定义支持的操作函数
OPERATION_FUNCTIONS = ["insertRow", "deleteRow", "updateRow"]

class TableOperation:
    """表格操作数据类"""

    def __init__(self, operation_type: str, table_index: int, **kwargs):
        self.operation_type = operation_type  # insertRow, deleteRow, updateRow
        self.table_index = table_index
        self.kwargs = kwargs

    def __str__(self):
        return f"{self.operation_type}({self.table_index}, {self.kwargs})"

class PromptHandler:
    """提示词处理器类"""

    def __init__(self, table_manager: TableManager):
        """
        初始化提示词处理器

        Args:
            table_manager: 表格管理器实例
        """
        self.logger = logging.getLogger(__name__)
        self.table_manager = table_manager
        self.system_prompt = MEMORY_TABLE_PROMPT

    def generate_prompt_with_tables(self, conversation_text: str, current_user_input: str = "", current_round: int = 0, use_integration_prompt: bool = False, input_tables_dir: str = None, batch_df=None) -> str:
        """
        生成包含表格状态的提示词，使用contents数组格式

        Args:
            conversation_text: 对话文本内容（已格式化的字符串，通常未使用）
            current_user_input: 当前用户的输入
            current_round: 当前轮次 (0-based索引)
            use_integration_prompt: 是否使用 MEMORY_TABLE_PROMPT_INTEGRATION
            input_tables_dir: 输入表格目录路径，用于获取其他表格的完整数据（压缩模式下使用）

        Returns:
            格式化的提示词
        """
        try:
            # 获取所有表格的内容
            table_contents = {}
            for table_index in range(6):  # 0-5个表格
                if use_integration_prompt and input_tables_dir and table_index != 4:
                    # 压缩模式：对于非表格4的其他表格，从输入目录获取完整数据
                    content = self._get_full_table_content_for_prompt(table_index, input_tables_dir)
                elif use_integration_prompt and table_index == 4 and batch_df is not None:
                    # 压缩模式：对于表格4，展示原始批次数据给AI理解
                    content = self._format_batch_df_for_prompt(batch_df)
                else:
                    # 正常模式：使用当前table_manager的数据
                    content = self.table_manager.get_table_content_for_prompt(table_index)
                table_contents[f"表格{table_index}内容"] = content

            # 根据参数选择使用哪个提示词模板
            if use_integration_prompt:
                memory_prompt = MEMORY_TABLE_PROMPT_INTEGRATION
            else:
                memory_prompt = MEMORY_TABLE_PROMPT
            for i in range(6):
                placeholder = f"{{表格{i}内容}}"
                table_content = table_contents.get(f"表格{i}内容", "")
                if BYPASS_ENHANCEMENT:
                    table_content = "'".join(c + "'" for c in table_content)  # 穿甲增强
                memory_prompt = memory_prompt.replace(placeholder, table_content)

            # 构建contents数组格式的提示词
            contents_parts = [
                # 1. 绕过内容过滤器的系统对话
                "contents:[",
                "{",
                "role:\"user\",",
                "parts:[",
                f"text:{BYPASSING_CONTENT_FILTERS_PROMPT}",
                "]",
                "},",
                "{",
                "role:\"model\",",
                "parts:[",
                f"text:{BYPASSING_CONTENT_FILTERS_PROMPT_MODEL}",
                "]",
                "},"
            ]

            # 2. 添加历史对话（不包括当前轮的用户输入）
            try:
                # 尝试获取实际的聊天数据
                import json
                import os
                chat_file = os.path.join("data", "chat.json")
                if os.path.exists(chat_file):
                    with open(chat_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                else:
                    messages = []

                                # 计算应该发送的历史消息数量：
                # 第1轮：发送第1条消息（索引0）
                # 第2轮：发送前3条消息（索引0-2）
                # 第3轮：发送前5条消息（索引0-4）
                # 规律：第n轮发送前(2*n-1)条消息，但不超过99条限制
                available_messages = len(messages)

                if current_round == 0:
                    # 第1轮：没有历史消息，只处理当前消息
                    desired_history_count = 0
                else:
                    # 第n轮：需要(2*current_round)条历史消息
                    # 第49轮：需要2*48=96条历史消息
                    # 第50轮：需要2*49=98条历史消息
                    desired_history_count = 2 * current_round

                # 应用最大上下文长度限制（减1是为了留给当前用户输入）
                max_history_allowed = MAX_CONTEXT_LENGTH - 1

                # 确定实际要发送的历史消息数量
                actual_count = min(desired_history_count, max_history_allowed, available_messages)

                                # 计算起始索引和结束索引
                if desired_history_count <= max_history_allowed:
                    # 如果期望的历史消息数量未超过上限，从第0条开始发送actual_count条
                    start_index = 0
                    history_messages_count = actual_count
                else:
                    # 如果期望的历史消息数量超过上限，使用滑动窗口
                    # 第50轮期望98条历史 -> 发送第0到97条（98条）- 刚好达到上限
                    # 第51轮期望100条历史 -> 发送第2到99条（98条）- 开始滑动
                    # 第52轮期望102条历史 -> 发送第4到101条（98条）
                    # 滑动窗口：每轮期望增加2条，但窗口固定98条
                    skip_count = desired_history_count - max_history_allowed
                    start_index = skip_count
                    history_messages_count = max_history_allowed

                    # 确保不会超出消息范围
                    if start_index + history_messages_count > available_messages:
                        # 如果滑动窗口超出了消息范围，调整到消息范围内的最新98条
                        start_index = available_messages - max_history_allowed
                        history_messages_count = max_history_allowed

                end_index = start_index + history_messages_count - 1
                current_processing_index = end_index + 1 if history_messages_count > 0 else 0
                if use_integration_prompt is False:
                    self.logger.info(f"第{current_round+1}轮：期望{desired_history_count}条历史消息，实际发送第{start_index}到{end_index}条历史消息（共{history_messages_count}条），当前处理第{current_processing_index}条，总消息{available_messages}条，最大上下文限制{MAX_CONTEXT_LENGTH}")

                # 添加历史对话到contents数组（从start_index开始）
                for i in range(start_index, start_index + history_messages_count):
                    message = messages[i]
                    role = message.get('role', '')
                    content = message.get('content', '')

                    # 转换role格式
                    if role == 'assistant':
                        role = 'model'
                    elif role == 'user':
                        role = 'user'
                    else:
                        continue  # 跳过未知角色

                    # 添加到contents数组（无制表符）
                    contents_parts.extend([
                        "{",
                        f"role:\"{role}\",",
                        "parts:[",
                        f"text:{content}",
                        "]",
                        "},"
                    ])

            except Exception as e:
                self.logger.warning(f"无法加载历史对话数据: {e}")

            # 3. 添加当前轮的表格分析指令（独立的最后一条用户消息）
            final_prompt = f"{memory_prompt}\n用户最新交互:{current_user_input}\n{END_PROMPT}"

            contents_parts.extend([
                "{",
                "role:\"user\",",
                "parts:[",
                f"text:{final_prompt}",
                "]",
                "},",
                "]"
            ])

            # 组合最终提示词（无制表符）
            result = '\n'.join(contents_parts)

            self.logger.debug(f"生成的提示词长度: {len(result)}")
            return result

        except Exception as e:
            self.logger.error(f"生成提示词失败: {e}")
            # 备用方案
            return self._generate_fallback_prompt(conversation_text, use_integration_prompt)

    def _add_role_content_to_parts(self, contents_parts: List[str], role: str, content_parts: List[str]):
        """
        将角色内容添加到contents数组中

        Args:
            contents_parts: contents数组部分
            role: 角色名称 ('user' 或 'model')
            content_parts: 内容部分列表
        """
        # 合并内容
        full_content = '\n'.join(content_parts)

        # 添加到contents数组
        contents_parts.extend([
            "{",
            f"role:\"{role}\",",
            "parts:[",
            f"text:{full_content}",
            "]",
            "},"
        ])

    def _generate_fallback_prompt(self, conversation_text: str, use_integration_prompt: bool = False) -> str:
        """
        生成备用提示词（当主要方法失败时使用）

        Args:
            conversation_text: 对话文本内容

        Returns:
            备用提示词
        """
        try:
            # 获取所有表格的内容
            table_contents = {}
            for table_index in range(6):
                content = self.table_manager.get_table_content_for_prompt(table_index)
                table_contents[f"表格{table_index}内容"] = content

            # 根据参数选择使用哪个提示词模板
            if use_integration_prompt:
                memory_prompt = MEMORY_TABLE_PROMPT_INTEGRATION
            else:
                memory_prompt = MEMORY_TABLE_PROMPT
            for i in range(6):
                placeholder = f"{{表格{i}内容}}"
                table_content = table_contents.get(f"表格{i}内容", "")
                memory_prompt = memory_prompt.replace(placeholder, table_content)

            # 构建简单的备用提示词
            fallback_prompt = f"""
{BYPASSING_CONTENT_FILTERS_PROMPT}

# 当前对话内容
{conversation_text}

{memory_prompt}

{END_PROMPT}
"""
            return fallback_prompt

        except Exception as e:
            self.logger.error(f"生成备用提示词也失败了: {e}")
            return f"{BYPASSING_CONTENT_FILTERS_PROMPT}\n\n{conversation_text}\n\n请分析对话并生成表格操作。"

    def extract_table_operations(self, response_text: str) -> List[TableOperation]:
        """
        从响应文本中提取表格操作指令

        Args:
            response_text: LLM响应文本

        Returns:
            表格操作列表
        """
        operations = []

        # 1. 首先尝试解析新的JSON格式
        json_operations = self._parse_json_format_operations(response_text)
        operations.extend(json_operations)

        # 2. 如果没有找到JSON格式，尝试解析<tableEdit>标签中的内容
        if not operations:
            pattern = r'<tableEdit>(.*?)</tableEdit>'
            matches = re.findall(pattern, response_text, re.DOTALL)

            for match in matches:
                # 首先尝试解析HTML注释包裹的新格式
                operations.extend(self._parse_html_comment_operations(match))
                # 然后尝试解析函数调用格式（向后兼容）
                operations.extend(self._parse_operations_from_text(match))
                # 最后尝试解析XML标签格式（向后兼容）
                operations.extend(self._parse_xml_operations(match))

        return operations

    def _parse_json_format_operations(self, response_text: str) -> List[TableOperation]:
        """
        解析新的JSON格式表格操作
        格式: {"tableEdit": [{"operation": "insertRow", "tableIndex": 0, "data": {...}}, ...]}

        Args:
            response_text: 响应文本

        Returns:
            操作列表
        """
        operations = []
        self.logger.info(f"开始解析JSON格式操作，文本内容: {response_text[:500]}...")

        try:
            # 查找JSON对象 - 改进的方法
            json_text = self._extract_json_from_text(response_text)

            if json_text:
                self.logger.info(f"提取的JSON文本: {json_text[:200]}...")

                # 解析JSON
                try:
                    data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON解析失败，尝试清理: {e}")
                    # 尝试清理JSON文本
                    json_text = self._clean_json_text(json_text)
                    self.logger.info(f"清理后的JSON文本: {json_text[:200]}...")
                    data = json.loads(json_text)

                # 提取操作列表
                table_edit_operations = data.get('tableEdit', [])
                self.logger.info(f"找到 {len(table_edit_operations)} 个JSON格式操作")

                for op_data in table_edit_operations:
                    operation = self._parse_single_json_operation(op_data)
                    if operation:
                        operations.append(operation)
                        self.logger.info(f"解析到JSON格式操作: {operation}")
            else:
                self.logger.info("未找到有效的JSON格式操作")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
        except Exception as e:
            self.logger.error(f"解析JSON格式操作失败: {e}")

        return operations

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        从文本中提取JSON对象
        """
        # 查找包含tableEdit的JSON对象
        start_markers = [
            '{"tableEdit"',
            '{ "tableEdit"',
            '{\n  "tableEdit"',
            '{\n "tableEdit"'
        ]

        start_idx = -1
        for marker in start_markers:
            idx = text.find(marker)
            if idx != -1:
                start_idx = idx
                break

        if start_idx == -1:
            # 尝试查找单独的tableEdit
            tableEdit_idx = text.find('"tableEdit"')
            if tableEdit_idx != -1:
                # 向前查找最近的 {
                for i in range(tableEdit_idx, -1, -1):
                    if text[i] == '{':
                        start_idx = i
                        break

        if start_idx == -1:
            return None

        # 从开始位置查找匹配的结束括号
        brace_count = 0
        end_idx = start_idx
        in_string = False
        escape_next = False

        for i in range(start_idx, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

        if brace_count == 0 and end_idx > start_idx:
            return text[start_idx:end_idx]

        return None

    def _clean_json_text(self, json_text: str) -> str:
        """清理JSON文本，修复常见的格式问题"""
        # 移除可能的注释
        json_text = re.sub(r'//.*?\n', '', json_text)
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)

        # 修复可能的尾随逗号
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)

        # 移除可能的多余空格和换行
        lines = json_text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)

        return ' '.join(cleaned_lines)

    def _parse_single_json_operation(self, op_data: Dict[str, Any]) -> Optional[TableOperation]:
        """
        解析单个JSON格式操作

        Args:
            op_data: 操作数据字典

        Returns:
            TableOperation对象或None
        """
        try:
            operation_type = op_data.get('operation')
            table_index = op_data.get('tableIndex')

            if operation_type not in OPERATION_FUNCTIONS:
                self.logger.warning(f"未知操作类型: {operation_type}")
                return None

            if table_index is None:
                self.logger.warning(f"缺少tableIndex: {op_data}")
                return None

            # 构造操作对象
            kwargs = {}

            if operation_type == "deleteRow":
                row_index = op_data.get('rowIndex')
                if row_index is None:
                    self.logger.warning(f"deleteRow操作缺少rowIndex: {op_data}")
                    return None
                kwargs['row_index'] = int(row_index)

            elif operation_type in ["insertRow", "updateRow"]:
                data = op_data.get('data', {})
                if not isinstance(data, dict):
                    self.logger.warning(f"无效的data格式: {data}")
                    return None

                # 转换字符串键为整数键
                converted_data = {}
                for key, value in data.items():
                    try:
                        int_key = int(key)
                        converted_data[int_key] = str(value)
                    except ValueError:
                        # 如果键不是数字，保留原始键
                        converted_data[key] = str(value)

                kwargs['data'] = converted_data

                if operation_type == "updateRow":
                    row_index = op_data.get('rowIndex')
                    if row_index is None:
                        self.logger.warning(f"updateRow操作缺少rowIndex: {op_data}")
                        return None
                    kwargs['row_index'] = int(row_index)

            return TableOperation(
                operation_type=operation_type,
                table_index=int(table_index),
                **kwargs
            )

        except Exception as e:
            self.logger.error(f"解析单个JSON操作失败: {e}, 数据: {op_data}")
            return None

    def _parse_operations_from_text(self, text: str) -> List[TableOperation]:
        """
        从文本中解析操作指令

        Args:
            text: 包含操作指令的文本

        Returns:
            操作列表
        """
        operations = []

        # 移除注释
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # 匹配各种操作函数
        for func_name in OPERATION_FUNCTIONS:
            pattern = rf'{func_name}\s*\(\s*(\d+)\s*,\s*(.+?)\s*\)'
            matches = re.findall(pattern, text, re.DOTALL)

            for match in matches:
                table_index = int(match[0])
                params_str = match[1].strip()

                try:
                    if func_name == "deleteRow":
                        # deleteRow(tableIndex, rowIndex)
                        row_index = int(params_str)
                        operation = TableOperation(
                            operation_type=func_name,
                            table_index=table_index,
                            row_index=row_index
                        )
                    elif func_name in ["insertRow", "updateRow"]:
                        # insertRow(tableIndex, data) 或 updateRow(tableIndex, rowIndex, data)
                        if func_name == "updateRow":
                            # 需要解析 rowIndex 和 data
                            parts = self._split_params(params_str)
                            if len(parts) >= 2:
                                row_index = int(parts[0].strip())
                                data_str = parts[1].strip()
                                data = self._parse_data_object(data_str)
                                operation = TableOperation(
                                    operation_type=func_name,
                                    table_index=table_index,
                                    row_index=row_index,
                                    data=data
                                )
                            else:
                                continue
                        else:
                            # insertRow 只需要 data
                            data = self._parse_data_object(params_str)
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                data=data
                            )
                    else:
                        continue

                    operations.append(operation)
                    self.logger.info(f"解析到操作: {operation}")

                except Exception as e:
                    self.logger.error(f"解析操作失败 {func_name}: {e}")
                    continue

        return operations

    def _split_params(self, params_str: str) -> List[str]:
        """
        分割参数字符串，处理嵌套的大括号
        """
        params = []
        current_param = ""
        brace_count = 0
        in_quotes = False
        quote_char = None

        for char in params_str:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == '{' and not in_quotes:
                brace_count += 1
            elif char == '}' and not in_quotes:
                brace_count -= 1
            elif char == ',' and brace_count == 0 and not in_quotes:
                params.append(current_param.strip())
                current_param = ""
                continue

            current_param += char

        if current_param.strip():
            params.append(current_param.strip())

        return params

    def _parse_data_object(self, data_str: str) -> Dict[int, Any]:
        """
        解析数据对象字符串

        Args:
            data_str: 数据对象字符串，如 '{0:"值1", 1:"值2"}'

        Returns:
            解析后的数据字典
        """
        try:
            # 尝试直接JSON解析
            data_str = data_str.strip()
            if data_str.startswith('{') and data_str.endswith('}'):
                # 处理JavaScript对象格式到JSON格式的转换
                # 替换数字键（JavaScript允许不带引号的数字键）
                data_str = re.sub(r'(\d+):', r'"\1":', data_str)
                # 将单引号替换为双引号
                data_str = data_str.replace("'", '"')

                # 解析JSON
                data_dict = json.loads(data_str)

                # 将字符串键转换为整数键
                result = {}
                for key, value in data_dict.items():
                    try:
                        int_key = int(key)
                        result[int_key] = value
                    except ValueError:
                        # 如果键不是数字，保留原始键
                        result[key] = value

                return result

        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试手动解析
            pass

        # 手动解析简单的对象格式
        result = {}
        data_str = data_str.strip('{}')

        # 分割键值对
        pairs = self._split_key_value_pairs(data_str)

        for pair in pairs:
            if ':' in pair:
                key_str, value_str = pair.split(':', 1)
                key_str = key_str.strip().strip('"\'')
                value_str = value_str.strip().strip('"\'')

                try:
                    key = int(key_str)
                except ValueError:
                    key = key_str

                result[key] = value_str

        return result

    def _split_key_value_pairs(self, data_str: str) -> List[str]:
        """分割键值对，处理嵌套引号"""
        pairs = []
        current_pair = ""
        in_quotes = False
        quote_char = None

        for char in data_str:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ',' and not in_quotes:
                if current_pair.strip():
                    pairs.append(current_pair.strip())
                current_pair = ""
                continue

            current_pair += char

        if current_pair.strip():
            pairs.append(current_pair.strip())

        return pairs

    def execute_operations(self, operations: List[TableOperation]) -> List[bool]:
        """
        执行表格操作列表

        Args:
            operations: 操作列表

        Returns:
            每个操作的执行结果列表
        """
        results = []

        for operation in operations:
            try:
                if operation.operation_type == "insertRow":
                    result = self.table_manager.insert_row(
                        operation.table_index,
                        operation.kwargs.get("data", {})
                    )
                elif operation.operation_type == "deleteRow":
                    result = self.table_manager.delete_row(
                        operation.table_index,
                        operation.kwargs.get("row_index", 0)
                    )
                elif operation.operation_type == "updateRow":
                    result = self.table_manager.update_row(
                        operation.table_index,
                        operation.kwargs.get("row_index", 0),
                        operation.kwargs.get("data", {})
                    )
                else:
                    self.logger.warning(f"未知操作类型: {operation.operation_type}")
                    result = False

                results.append(result)

                if result:
                    self.logger.info(f"成功执行操作: {operation}")
                else:
                    self.logger.error(f"执行操作失败: {operation}")

            except Exception as e:
                self.logger.error(f"执行操作异常 {operation}: {e}")
                results.append(False)

        return results

    def process_conversation_round(self, conversation_text: str, llm_response: str) -> Tuple[str, List[bool]]:
        """
        处理一轮对话的完整流程

        Args:
            conversation_text: 对话文本
            llm_response: LLM的响应（包含表格操作指令）

        Returns:
            (生成的提示词, 操作执行结果列表)
        """
        # 生成包含表格内容的提示词
        prompt = self.generate_prompt_with_tables(conversation_text)

        # 提取表格操作指令
        operations = self.extract_table_operations(llm_response)

        # 执行操作
        results = self.execute_operations(operations)

        return prompt, results

    def validate_operation(self, operation: TableOperation) -> bool:
        """
        验证操作的有效性

        Args:
            operation: 表格操作

        Returns:
            操作是否有效
        """
        # 检查表格索引是否有效
        if operation.table_index not in self.table_manager.schemas:
            self.logger.error(f"无效的表格索引: {operation.table_index}")
            return False

        # 根据操作类型进行进一步验证
        if operation.operation_type == "deleteRow":
            # 检查行索引是否存在
            df = self.table_manager.load_table(operation.table_index)
            row_index = operation.kwargs.get("row_index", -1)
            if row_index < 0 or row_index >= len(df):
                self.logger.error(f"无效的行索引: {row_index}")
                return False

        elif operation.operation_type in ["insertRow", "updateRow"]:
            # 检查数据字典是否有效
            data = operation.kwargs.get("data", {})
            if not isinstance(data, dict):
                self.logger.error(f"无效的数据格式: {data}")
                return False

            # 检查列索引是否有效
            schema = self.table_manager.schemas[operation.table_index]
            for col_index in data.keys():
                if isinstance(col_index, int) and col_index not in schema["columns"]:
                    self.logger.warning(f"表格 {operation.table_index} 中不存在列索引 {col_index}")

        return True

    def _parse_xml_operations(self, text: str) -> List[TableOperation]:
        """
        从文本中解析XML格式的操作指令
        支持格式如：<insertRow table="重要事件历史表格">...</insertRow>

        Args:
            text: 包含XML格式操作指令的文本

        Returns:
            操作列表
        """
        operations = []
        self.logger.info(f"开始解析XML格式操作，文本内容: {text[:500]}...")

        for func_name in OPERATION_FUNCTIONS:
            # 匹配XML标签格式
            pattern = rf'<{func_name}\s+table="([^"]+)"[^>]*>(.*?)</{func_name}>'
            matches = re.findall(pattern, text, re.DOTALL)
            self.logger.info(f"查找 {func_name} 操作，找到 {len(matches)} 个匹配")

            for match in matches:
                table_name = match[0].strip()
                content = match[1].strip()
                self.logger.info(f"解析操作: {func_name}, 表格: {table_name}, 内容: {content}")

                try:
                    # 根据表格名称查找索引
                    table_index = self._get_table_index_by_name(table_name)
                    self.logger.info(f"表格 '{table_name}' 对应索引: {table_index}")
                    if table_index is None:
                        self.logger.warning(f"未找到表格: {table_name}")
                        continue

                    if func_name in ["insertRow", "updateRow"]:
                        # 解析列表格式的数据
                        data = self._parse_list_format_data(content, table_index)
                        if data:
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                data=data
                            )
                            operations.append(operation)
                            self.logger.info(f"解析到XML格式操作: {operation}")
                    elif func_name == "deleteRow":
                        # 对于deleteRow，内容应该是行索引
                        try:
                            row_index = int(content.strip())
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                row_index=row_index
                            )
                            operations.append(operation)
                            self.logger.info(f"解析到XML格式操作: {operation}")
                        except ValueError:
                            self.logger.error(f"无法解析行索引: {content}")

                except Exception as e:
                    self.logger.error(f"解析XML格式操作失败 {func_name}: {e}")
                    continue

        return operations

    def _get_table_index_by_name(self, table_name: str) -> Optional[int]:
        """根据表格名称获取表格索引"""
        table_schemas = self.table_manager.schemas
        for index, schema in table_schemas.items():
            if schema['name'] == table_name:
                return index
        return None

    def _parse_list_format_data(self, content: str, table_index: int) -> Optional[Dict[int, Any]]:
        """
        解析列表格式的数据
        格式如：
        - 时间戳: 2024-12-16 14:30:00
        - 事件类型: 系统测试
        """
        try:
            data = {}
            schema = self.table_manager.schemas[table_index]
            columns = schema['columns']
            self.logger.info(f"开始解析列表格式数据，表格索引: {table_index}")
            self.logger.info(f"表格列定义: {columns}")
            self.logger.info(f"要解析的内容: {content}")

            # 按行分割
            lines = content.strip().split('\n')
            self.logger.info(f"分割后的行数: {len(lines)}")

            for line in lines:
                line = line.strip()
                self.logger.info(f"处理行: '{line}'")
                if line.startswith('- ') and ':' in line:
                    # 提取键值对
                    key_value = line[2:].strip()  # 去掉 "- "
                    if ':' in key_value:
                        key, value = key_value.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        self.logger.info(f"提取键值对: '{key}' = '{value}'")

                        # 查找对应的列索引
                        for col_index, col_name in columns.items():
                            if col_name == key:
                                data[col_index] = value
                                self.logger.info(f"匹配到列 {col_index}: {col_name} = {value}")
                                break
                        else:
                            self.logger.warning(f"未找到匹配的列名: '{key}'")

            self.logger.info(f"最终解析的数据: {data}")
            return data if data else None

        except Exception as e:
            self.logger.error(f"解析列表格式数据失败: {e}")
            return None

    def _parse_html_comment_operations(self, text: str) -> List[TableOperation]:
        """
        解析HTML注释包裹的操作指令
        格式: <!--
        insertRow(0, {"0":"十月","1":"冬天/下雪",...})
        deleteRow(1, 2)
        ...
        -->
        """
        operations = []
        self.logger.info(f"开始解析HTML注释包裹的操作，文本内容: {text[:500]}...")

        # 查找HTML注释中的内容
        comment_pattern = r'<!--(.*?)-->'
        comment_matches = re.findall(comment_pattern, text, re.DOTALL)
        self.logger.info(f"找到 {len(comment_matches)} 个HTML注释")

        for comment_content in comment_matches:
            comment_content = comment_content.strip()
            self.logger.info(f"解析注释内容: {comment_content[:200]}...")

            # 在注释内容中查找函数调用
            for func_name in OPERATION_FUNCTIONS:
                # 使用更精确的正则表达式来匹配函数调用
                if func_name == "deleteRow":
                    # deleteRow(tableIndex, rowIndex)
                    pattern = rf'{func_name}\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
                    matches = re.findall(pattern, comment_content)
                    for match in matches:
                        try:
                            table_index = int(match[0])
                            row_index = int(match[1])
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                row_index=row_index
                            )
                            operations.append(operation)
                            self.logger.info(f"解析到HTML注释操作: {operation}")
                        except Exception as e:
                            self.logger.error(f"解析deleteRow操作失败: {e}")

                else:
                    # insertRow 和 updateRow，需要解析JSON对象
                    if func_name == "updateRow":
                        # updateRow(tableIndex, rowIndex, {data})
                        pattern = rf'{func_name}\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\{{[^}}]*\}})\s*\)'
                    else:
                        # insertRow(tableIndex, {data})
                        pattern = rf'{func_name}\s*\(\s*(\d+)\s*,\s*(\{{[^}}]*\}})\s*\)'

                    matches = re.findall(pattern, comment_content)
                    for match in matches:
                        try:
                            table_index = int(match[0])
                            if func_name == "updateRow":
                                row_index = int(match[1])
                                json_str = match[2]
                            else:
                                row_index = None
                                json_str = match[1]

                            # 解析JSON数据
                            data = self._parse_json_data(json_str)
                            if data is not None:
                                if func_name == "updateRow":
                                    operation = TableOperation(
                                        operation_type=func_name,
                                        table_index=table_index,
                                        row_index=row_index,
                                        data=data
                                    )
                                else:
                                    operation = TableOperation(
                                        operation_type=func_name,
                                        table_index=table_index,
                                        data=data
                                    )
                                operations.append(operation)
                                self.logger.info(f"解析到HTML注释操作: {operation}")
                        except Exception as e:
                            self.logger.error(f"解析{func_name}操作失败: {e}")

        return operations

    def _parse_json_data(self, json_str: str) -> Optional[Dict[int, Any]]:
        """
        解析JSON数据字符串，支持数字键和字符串键
        """
        try:
            # 清理JSON字符串
            json_str = json_str.strip()

            # 处理可能的键值格式问题
            # 将数字键从字符串转换为实际数字键（但在JSON中仍然是字符串）
            json_str = re.sub(r'(\d+):', r'"\1":', json_str)  # 数字键加引号
            json_str = json_str.replace("'", '"')  # 单引号替换为双引号

            # 解析JSON
            data_dict = json.loads(json_str)

            # 将字符串键转换为整数键
            result = {}
            for key, value in data_dict.items():
                try:
                    int_key = int(key)
                    result[int_key] = value
                except ValueError:
                    # 如果键不是数字，保留原始键
                    result[key] = value

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {json_str}, 错误: {e}")
            return None
        except Exception as e:
            self.logger.error(f"数据解析异常: {e}")
            return None

    def generate_compression_prompt(self) -> str:
        """
        为表格压缩生成提示词，使用 MEMORY_TABLE_PROMPT_INTEGRATION

        Returns:
            格式化的压缩提示词
        """
        try:
            # 获取所有表格的内容
            table_contents = {}
            for table_index in range(6):  # 0-5个表格
                content = self.table_manager.get_table_content_for_prompt(table_index)
                table_contents[f"表格{table_index}内容"] = content

            # 填充 MEMORY_TABLE_PROMPT_INTEGRATION 中的表格内容占位符
            compression_prompt = MEMORY_TABLE_PROMPT_INTEGRATION
            for i in range(6):
                placeholder = f"{{表格{i}内容}}"
                table_content = table_contents.get(f"表格{i}内容", "")
                compression_prompt = compression_prompt.replace(placeholder, table_content)

            self.logger.debug(f"生成的压缩提示词长度: {len(compression_prompt)}")
            return compression_prompt

        except Exception as e:
            self.logger.error(f"生成压缩提示词失败: {e}")
            return ""

    def parse_table_operations(self, response_text: str) -> List[TableOperation]:
        """
        解析LLM响应中的表格操作
        这是 extract_table_operations 方法的别名，用于保持与 table_compression.py 的兼容性

        Args:
            response_text: LLM的响应文本

        Returns:
            解析出的表格操作列表
        """
        return self.extract_table_operations(response_text)

    def simulate_compression_response(self) -> str:
        """
        生成模拟的压缩响应，用于测试和开发

        Returns:
            模拟的LLM响应
        """
        mock_response = """
{
  "tableEdit": [
    {"operation": "insertRow", "tableIndex": 4, "data": {"0": "模拟角色", "1": "模拟事件简述", "2": "2024-01-01", "3": "模拟地点", "4": "模拟情绪"}}
  ]
}
        """
        self.logger.info("生成模拟压缩响应")
        return mock_response.strip()

    def _get_full_table_content_for_prompt(self, table_index: int, input_tables_dir: str) -> str:
        """
        从指定目录获取完整表格内容的格式化字符串，用于提示词

        Args:
            table_index: 表格索引
            input_tables_dir: 输入表格目录路径

        Returns:
            格式化的表格内容字符串
        """
        try:
            import os
            import pandas as pd

            if table_index not in TABLE_SCHEMAS:
                self.logger.error(f"无效的表格索引: {table_index}")
                return ""

            schema = TABLE_SCHEMAS[table_index]
            file_path = os.path.join(input_tables_dir, schema['file_name'])

            if not os.path.exists(file_path):
                self.logger.warning(f"表格文件不存在: {file_path}")
                return ""

            df = pd.read_csv(file_path, encoding='utf-8-sig')
            if df.empty:
                return ""

            lines = []
            for idx, row in df.iterrows():
                row_data = [str(idx)] + [str(row[col]) for col in df.columns]
                lines.append(",".join(row_data))

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"获取完整表格内容失败 {table_index}: {e}")
            return ""

    def _format_batch_df_for_prompt(self, batch_df) -> str:
        """
        将批次DataFrame格式化为提示词中的表格内容字符串

        Args:
            batch_df: 批次数据DataFrame

        Returns:
            格式化的表格内容字符串
        """
        try:
            if batch_df is None or batch_df.empty:
                return ""

            lines = []
            for idx, row in batch_df.iterrows():
                row_data = [str(idx)] + [str(row[col]) for col in batch_df.columns]
                lines.append(",".join(row_data))

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"格式化批次数据失败: {e}")
            return ""
