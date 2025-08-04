#!/usr/bin/env python3
"""
Prompt processing module
Responsible for generating prompts with table information and parsing LLM responses
"""

import re
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Optional
from prompt import MEMORY_TABLE_PROMPT, MEMORY_TABLE_PROMPT_INTEGRATION, BYPASSING_CONTENT_FILTERS_PROMPT, END_PROMPT, BYPASSING_CONTENT_FILTERS_PROMPT_MODEL  # Import system prompts and filter bypass prompts from prompt.py
from config import MAX_CONTEXT_LENGTH, BYPASS_ENHANCEMENT  # Import max context length configuration
from src.table_manager import TableManager
from src.table_schemas import TABLE_SCHEMAS

# Define supported operation functions
OPERATION_FUNCTIONS = ["insertRow", "deleteRow", "updateRow"]

class TableOperation:
    """Table operation data class"""

    def __init__(self, operation_type: str, table_index: int, **kwargs):
        self.operation_type = operation_type  # insertRow, deleteRow, updateRow
        self.table_index = table_index
        self.kwargs = kwargs

    def __str__(self):
        return f"{self.operation_type}({self.table_index}, {self.kwargs})"

class PromptManager:
    """Prompt handler class"""

    def __init__(self, table_manager: TableManager):
        """
        Initializes the prompt handler

        Args:
            table_manager: TableManager instance
        """
        self.logger = logging.getLogger(__name__)
        self.table_manager = table_manager
        self.system_prompt = MEMORY_TABLE_PROMPT

    def generate_prompt_with_tables(self, conversation_text: str, current_user_input: str = "", current_round: int = 0, use_integration_prompt: bool = False, input_tables_dir: Optional[str] = None, batch_df=None) -> str:
        """
        Generates a prompt with table status, using the contents array format

        Args:
            conversation_text: Conversation text content (formatted string, usually not used)
            current_user_input: The current user's input
            current_round: The current round (0-based index)
            use_integration_prompt: Whether to use MEMORY_TABLE_PROMPT_INTEGRATION
            input_tables_dir: Input tables directory path, for getting full data of other tables (used in compression mode)

        Returns:
            Formatted prompt
        """
        try:
            # Get the content of all tables
            table_contents = {}
            for table_index in range(6):  # Tables 0-5
                if use_integration_prompt and input_tables_dir and table_index != 4:
                    # Compression mode: for tables other than table 4, get full data from the input directory
                    content = self._get_full_table_content_for_prompt(table_index, input_tables_dir)
                elif use_integration_prompt and table_index == 4 and batch_df is not None:
                    # Compression mode: for table 4, show the original batch data for the AI to understand
                    content = self._format_batch_df_for_prompt(batch_df)
                else:
                    # Normal mode: use data from the current table_manager
                    content = self.table_manager.get_table_content_for_prompt(table_index)
                table_contents[f"Table{table_index}Content"] = content

            # Choose which prompt template to use based on the parameter
            if use_integration_prompt:
                memory_prompt = MEMORY_TABLE_PROMPT_INTEGRATION
            else:
                memory_prompt = MEMORY_TABLE_PROMPT
            for i in range(6):
                placeholder = f"{{Table{i}Content}}"
                table_content = table_contents.get(f"Table{i}Content", "")
                if BYPASS_ENHANCEMENT:
                    table_content = "'".join(c + "'" for c in table_content)  # Armor-piercing enhancement
                memory_prompt = memory_prompt.replace(placeholder, table_content)

            # Build the prompt in the contents array format
            contents_parts = [
                # 1. System dialog to bypass content filters
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

            # 2. Add historical conversation (excluding the current round's user input)
            try:
                # Try to get the actual chat data
                import json
                import os
                chat_file = os.path.join("data", "chat.json")
                if os.path.exists(chat_file):
                    with open(chat_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                else:
                    messages = []

                # Calculate the number of historical messages to send:
                # Round 1: send the 1st message (index 0)
                # Round 2: send the first 3 messages (index 0-2)
                # Round 3: send the first 5 messages (index 0-4)
                # Pattern: round n sends the first (2*n-1) messages, but not exceeding the 99 message limit
                available_messages = len(messages)

                if current_round == 0:
                    # Round 1: no historical messages, only process the current message
                    desired_history_count = 0
                else:
                    # Round n: need (2*current_round) historical messages
                    # Round 49: need 2*48=96 historical messages
                    # Round 50: need 2*49=98 historical messages
                    desired_history_count = 2 * current_round

                # Apply the maximum context length limit (subtract 1 to leave room for the current user input)
                max_history_allowed = MAX_CONTEXT_LENGTH - 1

                # Determine the actual number of historical messages to send
                actual_count = min(desired_history_count, max_history_allowed, available_messages)

                # Calculate the start and end indices
                if desired_history_count <= max_history_allowed:
                    # If the desired number of historical messages does not exceed the limit, send actual_count messages starting from index 0
                    start_index = 0
                    history_messages_count = actual_count
                else:
                    # If the desired number of historical messages exceeds the limit, use a sliding window
                    # Round 50 desires 98 historical messages -> send 0 to 97 (98 messages) - just at the limit
                    # Round 51 desires 100 historical messages -> send 2 to 99 (98 messages) - start sliding
                    # Round 52 desires 102 historical messages -> send 4 to 101 (98 messages)
                    # Sliding window: each round desires 2 more messages, but the window is fixed at 98 messages
                    skip_count = desired_history_count - max_history_allowed
                    start_index = skip_count
                    history_messages_count = max_history_allowed

                    # Ensure it does not exceed the message range
                    if start_index + history_messages_count > available_messages:
                        # If the sliding window exceeds the message range, adjust to the latest 98 messages within the range
                        start_index = available_messages - max_history_allowed
                        history_messages_count = max_history_allowed

                end_index = start_index + history_messages_count - 1
                current_processing_index = end_index + 1 if history_messages_count > 0 else 0
                if use_integration_prompt is False:
                    self.logger.info(f"Round {current_round+1}: Desired {desired_history_count} historical messages, actually sending messages {start_index} to {end_index} (total {history_messages_count}), currently processing message {current_processing_index}, total messages {available_messages}, max context limit {MAX_CONTEXT_LENGTH}")

                # Add historical conversation to the contents array (starting from start_index)
                for i in range(start_index, start_index + history_messages_count):
                    message = messages[i]
                    role = message.get('role', '')
                    content = message.get('content', '')

                    # Convert role format
                    if role == 'assistant':
                        role = 'model'
                    elif role == 'user':
                        role = 'user'
                    else:
                        continue  # Skip unknown roles

                    # Add to the contents array (without tabs)
                    contents_parts.extend([
                        "{",
                        f"role:\"{role}\",",
                        "parts:[",
                        f"text:{content}",
                        "]",
                        "},"
                    ])

            except Exception as e:
                self.logger.warning(f"Could not load historical conversation data: {e}")

            # 3. Add the current round's table analysis instruction (as a separate last user message)
            final_prompt = f"{memory_prompt}\nLatest user interaction:{current_user_input}\n{END_PROMPT}"

            contents_parts.extend([
                "{",
                "role:\"user\",",
                "parts:[",
                f"text:{final_prompt}",
                "]",
                "},",
                "]"
            ])

            # Combine the final prompt (without tabs)
            result = '\n'.join(contents_parts)

            self.logger.debug(f"Generated prompt length: {len(result)}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to generate prompt: {e}")
            # Fallback plan
            return self._generate_fallback_prompt(conversation_text, use_integration_prompt)

    def _add_role_content_to_parts(self, contents_parts: List[str], role: str, content_parts: List[str]):
        """
        Adds role content to the contents array

        Args:
            contents_parts: The contents array parts
            role: The role name ('user' or 'model')
            content_parts: The list of content parts
        """
        # Combine the content
        full_content = '\n'.join(content_parts)

        # Add to the contents array
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
        Generates a fallback prompt (used when the main method fails)

        Args:
            conversation_text: The conversation text content

        Returns:
            The fallback prompt
        """
        try:
            # Get the content of all tables
            table_contents = {}
            for table_index in range(6):
                content = self.table_manager.get_table_content_for_prompt(table_index)
                table_contents[f"Table{table_index}Content"] = content

            # Choose which prompt template to use based on the parameter
            if use_integration_prompt:
                memory_prompt = MEMORY_TABLE_PROMPT_INTEGRATION
            else:
                memory_prompt = MEMORY_TABLE_PROMPT
            for i in range(6):
                placeholder = f"{{Table{i}Content}}"
                table_content = table_contents.get(f"Table{i}Content", "")
                memory_prompt = memory_prompt.replace(placeholder, table_content)

            # Build a simple fallback prompt
            fallback_prompt = f"""
{BYPASSING_CONTENT_FILTERS_PROMPT}

# Current conversation content
{conversation_text}

{memory_prompt}

{END_PROMPT}
"""
            return fallback_prompt

        except Exception as e:
            self.logger.error(f"Failed to generate fallback prompt as well: {e}")
            return f"{BYPASSING_CONTENT_FILTERS_PROMPT}\n\n{conversation_text}\n\nPlease analyze the conversation and generate table operations."

    def extract_table_operations(self, response_text: str) -> List[TableOperation]:
        """
        Extracts table operation instructions from the response text

        Args:
            response_text: The LLM response text

        Returns:
            A list of table operations
        """
        operations = []

        # 1. First try to parse the new JSON format
        json_operations = self._parse_json_format_operations(response_text)
        operations.extend(json_operations)

        # 2. If no JSON format is found, try to parse the content within the <tableEdit> tag
        if not operations:
            pattern = r'<tableEdit>(.*?)</tableEdit>'
            matches = re.findall(pattern, response_text, re.DOTALL)

            for match in matches:
                # First try to parse the new format wrapped in HTML comments
                operations.extend(self._parse_html_comment_operations(match))
                # Then try to parse the function call format (for backward compatibility)
                operations.extend(self._parse_operations_from_text(match))
                # Finally try to parse the XML tag format (for backward compatibility)
                operations.extend(self._parse_xml_operations(match))

        return operations

    def _parse_json_format_operations(self, response_text: str) -> List[TableOperation]:
        """
        Parses the new JSON format table operations
        Format: {"tableEdit": [{"operation": "insertRow", "tableIndex": 0, "data": {...}}, ...]}

        Args:
            response_text: The response text

        Returns:
            A list of operations
        """
        operations = []
        self.logger.info(f"Starting to parse JSON format operations, text content: {response_text[:500]}...")

        try:
            # Find the JSON object - improved method
            json_text = self._extract_json_from_text(response_text)

            if json_text:
                self.logger.info(f"Extracted JSON text: {json_text[:200]}...")

                # Parse the JSON
                try:
                    data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON parsing failed, trying to clean it up: {e}")
                    # Try to clean up the JSON text
                    json_text = self._clean_json_text(json_text)
                    self.logger.info(f"Cleaned JSON text: {json_text[:200]}...")
                    data = json.loads(json_text)

                # Extract the list of operations
                table_edit_operations = data.get('tableEdit', [])
                self.logger.info(f"Found {len(table_edit_operations)} JSON format operations")

                for op_data in table_edit_operations:
                    operation = self._parse_single_json_operation(op_data)
                    if operation:
                        operations.append(operation)
                        self.logger.info(f"Parsed JSON format operation: {operation}")
            else:
                self.logger.info("No valid JSON format operations found")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to parse JSON format operations: {e}")

        return operations

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extracts a JSON object from the text
        """
        # Find a JSON object containing tableEdit
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
            # Try to find tableEdit alone
            tableEdit_idx = text.find('"tableEdit"')
            if tableEdit_idx != -1:
                # Find the nearest { before it
                for i in range(tableEdit_idx, -1, -1):
                    if text[i] == '{':
                        start_idx = i
                        break

        if start_idx == -1:
            return None

        # Find the matching closing brace from the start position
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
        """Cleans up JSON text, fixing common formatting issues"""
        # Remove possible comments
        json_text = re.sub(r'//.*?\n', '', json_text)
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)

        # Fix possible trailing commas
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)

        # Remove possible extra spaces and newlines
        lines = json_text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)

        return ' '.join(cleaned_lines)

    def _parse_single_json_operation(self, op_data: Dict[str, Any]) -> Optional[TableOperation]:
        """
        Parses a single JSON format operation

        Args:
            op_data: The operation data dictionary

        Returns:
            A TableOperation object or None
        """
        try:
            operation_type = op_data.get('operation')
            table_index = op_data.get('tableIndex')

            if operation_type not in OPERATION_FUNCTIONS:
                self.logger.warning(f"Unknown operation type: {operation_type}")
                return None

            if table_index is None:
                self.logger.warning(f"Missing tableIndex: {op_data}")
                return None

            # Construct the operation object
            kwargs = {}

            if operation_type == "deleteRow":
                row_index = op_data.get('rowIndex')
                if row_index is None:
                    self.logger.warning(f"deleteRow operation missing rowIndex: {op_data}")
                    return None
                kwargs['row_index'] = int(row_index)

            elif operation_type in ["insertRow", "updateRow"]:
                data = op_data.get('data', {})
                if not isinstance(data, dict):
                    self.logger.warning(f"Invalid data format: {data}")
                    return None

                # Convert string keys to integer keys
                converted_data = {}
                for key, value in data.items():
                    try:
                        int_key = int(key)
                        converted_data[int_key] = str(value)
                    except ValueError:
                        # If the key is not a number, keep the original key
                        converted_data[key] = str(value)

                kwargs['data'] = converted_data

                if operation_type == "updateRow":
                    row_index = op_data.get('rowIndex')
                    if row_index is None:
                        self.logger.warning(f"updateRow operation missing rowIndex: {op_data}")
                        return None
                    kwargs['row_index'] = int(row_index)

            return TableOperation(
                operation_type=operation_type,
                table_index=int(table_index),
                **kwargs
            )

        except Exception as e:
            self.logger.error(f"Failed to parse single JSON operation: {e}, data: {op_data}")
            return None

    def _parse_operations_from_text(self, text: str) -> List[TableOperation]:
        """
        Parses operation instructions from text

        Args:
            text: The text containing operation instructions

        Returns:
            A list of operations
        """
        operations = []

        # Remove comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # Match various operation functions
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
                        # insertRow(tableIndex, data) or updateRow(tableIndex, rowIndex, data)
                        if func_name == "updateRow":
                            # Need to parse rowIndex and data
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
                            # insertRow only needs data
                            data = self._parse_data_object(params_str)
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                data=data
                            )
                    else:
                        continue

                    operations.append(operation)
                    self.logger.info(f"Parsed operation: {operation}")

                except Exception as e:
                    self.logger.error(f"Failed to parse operation {func_name}: {e}")
                    continue

        return operations

    def _split_params(self, params_str: str) -> List[str]:
        """
        Splits a parameter string, handling nested braces
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
        Parses a data object string

        Args:
            data_str: A data object string, e.g., '{0:"Value1", 1:"Value2"}'

        Returns:
            A parsed data dictionary
        """
        try:
            # Try direct JSON parsing
            data_str = data_str.strip()
            if data_str.startswith('{') and data_str.endswith('}'):
                # Handle conversion from JavaScript object format to JSON format
                # Replace numeric keys (JavaScript allows unquoted numeric keys)
                data_str = re.sub(r'(\d+):', r'"\1":', data_str)
                # Replace single quotes with double quotes
                data_str = data_str.replace("'", '"')

                # Parse JSON
                data_dict = json.loads(data_str)

                # Convert string keys to integer keys
                result = {}
                for key, value in data_dict.items():
                    try:
                        int_key = int(key)
                        result[int_key] = value
                    except ValueError:
                        # If the key is not a number, keep the original key
                        result[key] = value

                return result

        except json.JSONDecodeError:
            # If JSON parsing fails, try manual parsing
            pass

        # Manually parse simple object formats
        result = {}
        data_str = data_str.strip('{}')

        # Split key-value pairs
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
        """Splits key-value pairs, handling nested quotes"""
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
        Executes a list of table operations

        Args:
            operations: The list of operations

        Returns:
            A list of execution results for each operation
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
                    self.logger.warning(f"Unknown operation type: {operation.operation_type}")
                    result = False

                results.append(result)

                if result:
                    self.logger.info(f"Successfully executed operation: {operation}")
                else:
                    self.logger.error(f"Failed to execute operation: {operation}")

            except Exception as e:
                self.logger.error(f"Exception executing operation {operation}: {e}")
                results.append(False)

        return results

    def process_conversation_round(self, conversation_text: str, llm_response: str) -> Tuple[str, List[bool]]:
        """
        Processes a full conversation round

        Args:
            conversation_text: The conversation text
            llm_response: The LLM's response (containing table operation instructions)

        Returns:
            (The generated prompt, a list of operation execution results)
        """
        # Generate a prompt with table contents
        prompt = self.generate_prompt_with_tables(conversation_text)

        # Extract table operation instructions
        operations = self.extract_table_operations(llm_response)

        # Execute operations
        results = self.execute_operations(operations)

        return prompt, results

    def validate_operation(self, operation: TableOperation) -> bool:
        """
        Validates an operation

        Args:
            operation: The table operation

        Returns:
            Whether the operation is valid
        """
        # Check if the table index is valid
        if operation.table_index not in self.table_manager.schemas:
            self.logger.error(f"Invalid table index: {operation.table_index}")
            return False

        # Further validation based on operation type
        if operation.operation_type == "deleteRow":
            # Check if the row index exists
            df = self.table_manager.load_table(operation.table_index)
            row_index = operation.kwargs.get("row_index", -1)
            if row_index < 0 or row_index >= len(df):
                self.logger.error(f"Invalid row index: {row_index}")
                return False

        elif operation.operation_type in ["insertRow", "updateRow"]:
            # Check if the data dictionary is valid
            data = operation.kwargs.get("data", {})
            if not isinstance(data, dict):
                self.logger.error(f"Invalid data format: {data}")
                return False

            # Check if the column indices are valid
            schema = self.table_manager.schemas[operation.table_index]
            for col_index in data.keys():
                if isinstance(col_index, int) and col_index not in schema["columns"]:
                    self.logger.warning(f"Column index {col_index} does not exist in table {operation.table_index}")

        return True

    def _parse_xml_operations(self, text: str) -> List[TableOperation]:
        """
        Parses XML format operation instructions from text
        Supports formats like: <insertRow table="Important Events History Table">...</insertRow>

        Args:
            text: The text containing XML format operation instructions

        Returns:
            A list of operations
        """
        operations = []
        self.logger.info(f"Starting to parse XML format operations, text content: {text[:500]}...")

        for func_name in OPERATION_FUNCTIONS:
            # Match XML tag format
            pattern = rf'<{func_name}\s+table="([^"]+)"[^>]*>(.*?)</{func_name}>'
            matches = re.findall(pattern, text, re.DOTALL)
            self.logger.info(f"Searching for {func_name} operation, found {len(matches)} matches")

            for match in matches:
                table_name = match[0].strip()
                content = match[1].strip()
                self.logger.info(f"Parsing operation: {func_name}, table: {table_name}, content: {content}")

                try:
                    # Find the index by table name
                    table_index = self._get_table_index_by_name(table_name)
                    self.logger.info(f"Table '{table_name}' corresponds to index: {table_index}")
                    if table_index is None:
                        self.logger.warning(f"Table not found: {table_name}")
                        continue

                    if func_name in ["insertRow", "updateRow"]:
                        # Parse list format data
                        data = self._parse_list_format_data(content, table_index)
                        if data:
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                data=data
                            )
                            operations.append(operation)
                            self.logger.info(f"Parsed XML format operation: {operation}")
                    elif func_name == "deleteRow":
                        # For deleteRow, the content should be the row index
                        try:
                            row_index = int(content.strip())
                            operation = TableOperation(
                                operation_type=func_name,
                                table_index=table_index,
                                row_index=row_index
                            )
                            operations.append(operation)
                            self.logger.info(f"Parsed XML format operation: {operation}")
                        except ValueError:
                            self.logger.error(f"Could not parse row index: {content}")

                except Exception as e:
                    self.logger.error(f"Failed to parse XML format operation {func_name}: {e}")
                    continue

        return operations

    def _get_table_index_by_name(self, table_name: str) -> Optional[int]:
        """Gets the table index by table name"""
        table_schemas = self.table_manager.schemas
        for index, schema in table_schemas.items():
            if schema['name'] == table_name:
                return index
        return None

    def _parse_list_format_data(self, content: str, table_index: int) -> Optional[Dict[int, Any]]:
        """
        Parses list format data
        Format like:
        - Timestamp: 2024-12-16 14:30:00
        - Event Type: System Test
        """
        try:
            data = {}
            schema = self.table_manager.schemas[table_index]
            columns = schema['columns']
            self.logger.info(f"Starting to parse list format data, table index: {table_index}")
            self.logger.info(f"Table column definitions: {columns}")
            self.logger.info(f"Content to parse: {content}")

            # Split by line
            lines = content.strip().split('\n')
            self.logger.info(f"Number of lines after splitting: {len(lines)}")

            for line in lines:
                line = line.strip()
                self.logger.info(f"Processing line: '{line}'")
                if line.startswith('- ') and ':' in line:
                    # Extract key-value pair
                    key_value = line[2:].strip()  # Remove "- "
                    if ':' in key_value:
                        key, value = key_value.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        self.logger.info(f"Extracted key-value pair: '{key}' = '{value}'")

                        # Find the corresponding column index
                        for col_index, col_name in columns.items():
                            if col_name == key:
                                data[col_index] = value
                                self.logger.info(f"Matched column {col_index}: {col_name} = {value}")
                                break
                        else:
                            self.logger.warning(f"No matching column name found: '{key}'")

            self.logger.info(f"Finally parsed data: {data}")
            return data if data else None

        except Exception as e:
            self.logger.error(f"Failed to parse list format data: {e}")
            return None

    def _parse_html_comment_operations(self, text: str) -> List[TableOperation]:
        """
        Parses operation instructions wrapped in HTML comments
        Format: <!--
        insertRow(0, {"0":"October","1":"Winter/Snow",...})
        deleteRow(1, 2)
        ...
        -->
        """
        operations = []
        self.logger.info(f"Starting to parse operations wrapped in HTML comments, text content: {text[:500]}...")

        # Find content within HTML comments
        comment_pattern = r'<!--(.*?)-->'
        comment_matches = re.findall(comment_pattern, text, re.DOTALL)
        self.logger.info(f"Found {len(comment_matches)} HTML comments")

        for comment_content in comment_matches:
            comment_content = comment_content.strip()
            self.logger.info(f"Parsing comment content: {comment_content[:200]}...")

            # Find function calls within the comment content
            for func_name in OPERATION_FUNCTIONS:
                # Use a more precise regular expression to match function calls
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
                            self.logger.info(f"Parsed HTML comment operation: {operation}")
                        except Exception as e:
                            self.logger.error(f"Failed to parse deleteRow operation: {e}")

                else:
                    # insertRow and updateRow, need to parse a JSON object
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

                            # Parse JSON data
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
                                self.logger.info(f"Parsed HTML comment operation: {operation}")
                        except Exception as e:
                            self.logger.error(f"Failed to parse {func_name} operation: {e}")

        return operations

    def _parse_json_data(self, json_str: str) -> Optional[Dict[int, Any]]:
        """
        Parses a JSON data string, supporting numeric and string keys
        """
        try:
            # Clean up the JSON string
            json_str = json_str.strip()

            # Handle possible key-value format issues
            # Convert numeric keys from strings to actual numeric keys (but still as strings in JSON)
            json_str = re.sub(r'(\d+):', r'"\1":', json_str)  # Add quotes to numeric keys
            json_str = json_str.replace("'", '"')  # Replace single quotes with double quotes

            # Parse JSON
            data_dict = json.loads(json_str)

            # Convert string keys to integer keys
            result = {}
            for key, value in data_dict.items():
                try:
                    int_key = int(key)
                    result[int_key] = value
                except ValueError:
                    # If the key is not a number, keep the original key
                    result[key] = value

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {json_str}, error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Data parsing exception: {e}")
            return None

    def generate_compression_prompt(self) -> str:
        """
        Generates a prompt for table compression, using MEMORY_TABLE_PROMPT_INTEGRATION

        Returns:
            Formatted compression prompt
        """
        try:
            # Get the content of all tables
            table_contents = {}
            for table_index in range(6):  # Tables 0-5
                content = self.table_manager.get_table_content_for_prompt(table_index)
                table_contents[f"Table{table_index}Content"] = content

            # Fill in the table content placeholders in MEMORY_TABLE_PROMPT_INTEGRATION
            compression_prompt = MEMORY_TABLE_PROMPT_INTEGRATION
            for i in range(6):
                placeholder = f"{{Table{i}Content}}"
                table_content = table_contents.get(f"Table{i}Content", "")
                compression_prompt = compression_prompt.replace(placeholder, table_content)

            self.logger.debug(f"Generated compression prompt length: {len(compression_prompt)}")
            return compression_prompt

        except Exception as e:
            self.logger.error(f"Failed to generate compression prompt: {e}")
            return ""

    def parse_table_operations(self, response_text: str) -> List[TableOperation]:
        """
        Parses table operations from the LLM response
        This is an alias for the extract_table_operations method, for compatibility with table_compression.py

        Args:
            response_text: The LLM's response text

        Returns:
            A list of parsed table operations
        """
        return self.extract_table_operations(response_text)

    def simulate_compression_response(self) -> str:
        """
        Generates a mock compression response, for testing and development

        Returns:
            A mock LLM response
        """
        mock_response = """
{
  "tableEdit": [
    {"operation": "insertRow", "tableIndex": 4, "data": {"0": "Mock Character", "1": "Mock Event Summary", "2": "2024-01-01", "3": "Mock Location", "4": "Mock Emotion"}}
  ]
}
        """
        self.logger.info("Generated mock compression response")
        return mock_response.strip()

    def _get_full_table_content_for_prompt(self, table_index: int, input_tables_dir: str) -> str:
        """
        Gets a formatted string of the full table content from a specified directory, for use in a prompt

        Args:
            table_index: The table index
            input_tables_dir: The input tables directory path

        Returns:
            A formatted string of the table content
        """
        try:
            import os
            import pandas as pd

            if table_index not in TABLE_SCHEMAS:
                self.logger.error(f"Invalid table index: {table_index}")
                return ""

            schema = TABLE_SCHEMAS[table_index]
            file_path = os.path.join(input_tables_dir, schema['file_name'])

            if not os.path.exists(file_path):
                self.logger.warning(f"Table file not found: {file_path}")
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
            self.logger.error(f"Failed to get full table content for {table_index}: {e}")
            return ""

    def _format_batch_df_for_prompt(self, batch_df) -> str:
        """
        Formats a batch DataFrame into a table content string for a prompt

        Args:
            batch_df: The batch data DataFrame

        Returns:
            A formatted string of the table content
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
            self.logger.error(f"Failed to format batch data: {e}")
            return ""
