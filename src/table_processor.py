#!/usr/bin/env python3
"""
表格处理器 - 将表格数据转换为特定JSON格式
"""

import json
import uuid
from typing import Dict, Any, List

from src.table_manager import TableManager
from src.table_schemas import get_all_table_schemas


class TableProcessor:
    """表格处理器，负责将表格数据转换为特定的JSON格式"""

    def __init__(self, table_manager: TableManager):
        self.table_manager = table_manager
        self.schemas = get_all_table_schemas()

    def generate_sheet_uid(self) -> str:
        """生成表格的唯一标识符"""
        return f"sheet_{uuid.uuid4().hex[:8]}"

    def create_source_data(self, schema: Dict[str, Any]) -> Dict[str, str]:
        """创建sourceData配置"""
        source_data = {
            "note": schema.get("description", ""),
            "initNode": "",
            "deleteNode": "",
            "updateNode": "",
            "insertNode": ""
        }

        # 从triggers中提取节点信息
        triggers = schema.get("triggers", {})
        if "insert" in triggers:
            source_data["insertNode"] = triggers["insert"]
        if "delete" in triggers:
            source_data["deleteNode"] = triggers["delete"]
        if "update" in triggers:
            source_data["updateNode"] = triggers["update"]

        # 根据表格类型设置特殊的initNode
        table_name = schema.get("name", "")
        if "时空" in table_name:
            source_data["initNode"] = "本轮需要记录当前时间、地点、人物信息，使用insertRow函数"
        elif "角色特征" in table_name or "角色与" in table_name or "重要事件" in table_name:
            source_data["initNode"] = "本轮必须从上文寻找已知的所有角色使用insertRow插入，角色名不能为空"

        return source_data

    def get_table_content(self, table_index: int) -> List[List]:
        """获取表格内容数据"""
        try:
            # 获取表格数据
            data = self.table_manager.get_table_data(table_index)

            if not data:
                # 如果表格为空，返回只有表头的数据
                schema = self.schemas.get(table_index, {})
                columns = schema.get("columns", {})
                header = [None] + [columns.get(i, f"列{i}") for i in sorted(columns.keys())]
                return [header]

            # 转换数据格式
            content = []

            # 添加表头行
            if data:
                schema = self.schemas.get(table_index, {})
                columns = schema.get("columns", {})
                header = [None] + [columns.get(i, f"列{i}") for i in sorted(columns.keys())]
                content.append(header)

                # 添加数据行
                for row in data:
                    # 在每行前面添加一个None值
                    content_row = [None] + row
                    content.append(content_row)

            return content
        except Exception as e:
            print(f"获取表格 {table_index} 内容时出错: {e}")
            # 返回只有表头的空表格
            schema = self.schemas.get(table_index, {})
            columns = schema.get("columns", {})
            header = [None] + [columns.get(i, f"列{i}") for i in sorted(columns.keys())]
            return [header]

    def determine_required_status(self, table_index: int) -> bool:
        """确定表格是否为必需的"""
        # 根据表格类型确定是否必需
        schema = self.schemas.get(table_index, {})
        table_name = schema.get("name", "")

        # 时空表格、角色特征表格、角色社交表格、重要事件表格通常是必需的
        required_keywords = ["时空", "角色特征", "角色与", "重要事件"]
        return any(keyword in table_name for keyword in required_keywords)

    def convert_to_json_format(self) -> Dict[str, Any]:
        """将所有表格转换为指定的JSON格式"""
        result = {}

        for table_index, schema in self.schemas.items():
            # 生成唯一的表格ID
            sheet_uid = self.generate_sheet_uid()

            # 获取表格内容
            content = self.get_table_content(table_index)

            # 创建表格配置
            sheet_config = {
                "uid": sheet_uid,
                "name": schema.get("name", f"表格{table_index}"),
                "domain": "chat",
                "type": "dynamic",
                "enable": True,
                "required": self.determine_required_status(table_index),
                "tochat": True,
                "triggerSend": False,
                "triggerSendDeep": 1,
                "config": {
                    "toChat": True,
                    "useCustomStyle": False,
                    "selectedCustomStyleKey": "",
                    "customStyles": {
                        "自定义样式": {
                            "mode": "regex",
                            "basedOn": "html",
                            "regex": "/(^[\\s\\S]*$)/g",
                            "replace": "$1"
                        }
                    }
                },
                "sourceData": self.create_source_data(schema),
                "content": content
            }

            result[sheet_uid] = sheet_config

        # 添加mate信息
        result["mate"] = {
            "type": "chatSheets",
            "version": 1
        }

        return result

    def save_to_file(self, output_file: str) -> bool:
        """保存JSON格式到文件"""
        try:
            json_data = self.convert_to_json_format()

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 表格数据已保存到: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return False

    def print_json_format(self) -> None:
        """打印JSON格式到控制台"""
        try:
            json_data = self.convert_to_json_format()
            print(json.dumps(json_data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"❌ 生成JSON格式失败: {e}")


def process_tables_to_json(table_manager: TableManager, output_file: str = None) -> Dict[str, Any]:
    """
    处理表格数据并转换为JSON格式

    Args:
        table_manager: 表格管理器实例
        output_file: 输出文件路径（可选）

    Returns:
        转换后的JSON数据
    """
    processor = TableProcessor(table_manager)

    # 转换为JSON格式
    json_data = processor.convert_to_json_format()

    # 如果指定了输出文件，则保存
    if output_file:
        processor.save_to_file(output_file)

    return json_data
