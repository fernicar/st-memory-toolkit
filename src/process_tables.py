#!/usr/bin/env python3
"""
表格处理脚本 - 将CSV表格文件转换为指定的JSON格式
"""

import os
import csv
import json
import uuid
from typing import Dict, Any, List


class CSVTableProcessor:
    """CSV表格处理器"""

    def __init__(self, tables_dir: str):
        self.tables_dir = tables_dir

        # 表格配置映射
        self.table_configs = {
            "spacetime_table.csv": {
                "name": "时空表格",
                "note": "记录时空信息的表格，应保持在一行",
                "initNode": "本轮需要记录当前时间、地点、人物信息，使用insertRow函数",
                "deleteNode": "此表大于一行时应删除多余行",
                "updateNode": "当描写的场景，时间，人物变更时",
                "required": True
            },
            "character_traits_table.csv": {
                "name": "角色特征表格",
                "note": "角色天生或不易改变的特征csv表格，思考本轮有否有其中的角色，他应作出什么反应",
                "initNode": "本轮必须从上文寻找已知的所有角色使用insertRow插入，角色名不能为空",
                "deleteNode": "",
                "updateNode": "当角色的身体出现持久性变化时，例如伤痕/当角色有新的爱好，职业，喜欢的事物时/当角色更换住所时/当角色提到重要信息时",
                "insertNode": "当本轮出现表中没有的新角色时，应插入",
                "required": True
            },
            "social_relations_table.csv": {
                "name": "角色与<user>社交表格",
                "note": "思考如果有角色和<user>互动，应什么态度",
                "initNode": "本轮必须从上文寻找已知的所有角色使用insertRow插入，角色名不能为空",
                "deleteNode": "",
                "updateNode": "当角色和<user>的交互不再符合原有的记录时/当角色和<user>的关系改变时",
                "insertNode": "当本轮出现表中没有的新角色时，应插入",
                "required": True
            },
            "tasks_table.csv": {
                "name": "任务、命令或者约定表格",
                "note": "思考本轮是否应该执行任务/赴约",
                "initNode": "",
                "deleteNode": "当大家赴约时/任务或命令完成时/任务，命令或约定被取消时",
                "updateNode": "",
                "insertNode": "当特定时间约定一起去做某事时/某角色收到做某事的命令或任务时",
                "required": False
            },
            "important_events_table.csv": {
                "name": "重要事件历史表格",
                "note": "记录<user>或角色经历的重要事件",
                "initNode": "本轮必须从上文寻找可以插入的事件并使用insertRow插入",
                "deleteNode": "",
                "updateNode": "",
                "insertNode": "当某个角色经历让自己印象深刻的事件时，比如表白、分手等",
                "required": True
            },
            "important_items_table.csv": {
                "name": "重要物品表格",
                "note": "对某人很贵重或有特殊纪念意义的物品",
                "initNode": "",
                "deleteNode": "",
                "updateNode": "",
                "insertNode": "当某人获得了贵重或有特殊意义的物品时/当某个已有物品有了特殊意义时",
                "required": False
            }
        }

    def generate_sheet_uid(self) -> str:
        """生成表格的唯一标识符"""
        return f"sheet_{uuid.uuid4().hex[:8]}"

    def read_csv_file(self, file_path: str) -> List[List]:
        """读取CSV文件并返回内容数组"""
        content = []

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)

                if not rows:
                    return content

                # 获取文件名
                file_name = os.path.basename(file_path)

                # 添加表头行，第一列为null
                header = [None] + rows[0]

                # 修正社交表格的表头
                if file_name == "social_relations_table.csv" and len(header) > 1:
                    # 替换表头中的"真银铃"为"<user>"
                    for i in range(1, len(header)):
                        if header[i] and "真银铃" in header[i]:
                            header[i] = header[i].replace("真银铃", "<user>")

                content.append(header)

                # 添加数据行，第一列为null
                for row in rows[1:]:
                    if row:  # 跳过空行
                        data_row = [None] + row
                        content.append(data_row)

        except Exception as e:
            print(f"读取CSV文件失败 {file_path}: {e}")

        return content

    def create_sheet_config(self, file_name: str, content: List[List]) -> Dict[str, Any]:
        """创建单个表格的配置"""
        config = self.table_configs.get(file_name, {})
        sheet_uid = self.generate_sheet_uid()

        return {
            "uid": sheet_uid,
            "name": config.get("name", file_name),
            "domain": "chat",
            "type": "dynamic",
            "enable": True,
            "required": config.get("required", False),
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
            "sourceData": {
                "note": config.get("note", ""),
                "initNode": config.get("initNode", ""),
                "deleteNode": config.get("deleteNode", ""),
                "updateNode": config.get("updateNode", ""),
                "insertNode": config.get("insertNode", "")
            },
            "content": content
        }

    def process_all_tables(self) -> Dict[str, Any]:
        """处理所有表格文件并生成JSON格式"""
        result = {}

        # 处理所有CSV文件
        for file_name in self.table_configs.keys():
            file_path = os.path.join(self.tables_dir, file_name)

            if os.path.exists(file_path):
                print(f"处理文件: {file_name}")
                content = self.read_csv_file(file_path)

                if not content:
                    # 如果文件为空，创建只有表头的内容
                    if file_name == "spacetime_table.csv":
                        content = [[None, "日期", "时间", "地点（当前描写）", "此地角色"]]
                    elif file_name == "character_traits_table.csv":
                        content = [[None, "角色名", "身体特征", "性格", "职业", "爱好", "喜欢的事物（作品、虚拟人物、物品等）", "住所", "其他重要信息"]]
                    elif file_name == "social_relations_table.csv":
                        content = [[None, "角色名", "对<user>关系", "对<user>态度", "对<user>好感"]]
                    elif file_name == "tasks_table.csv":
                        content = [[None, "角色", "任务", "地点", "持续时间"]]
                    elif file_name == "important_events_table.csv":
                        content = [[None, "角色", "事件简述", "日期", "地点", "情绪"]]
                    elif file_name == "important_items_table.csv":
                        content = [[None, "拥有人", "物品描述", "物品名", "重要原因"]]

                sheet_config = self.create_sheet_config(file_name, content)
                result[sheet_config["uid"]] = sheet_config
            else:
                print(f"文件不存在: {file_path}")

        # 添加mate信息
        result["mate"] = {
            "type": "chatSheets",
            "version": 1
        }

        return result

    def save_to_file(self, output_file: str, json_data: Dict[str, Any]) -> bool:
        """保存JSON格式到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 表格数据已保存到: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return False


def process_tables_in_directory(tables_dir: str, output_file: str = None) -> Dict[str, Any]:
    """
    处理指定目录中的表格文件

    Args:
        tables_dir: 表格目录路径
        output_file: 输出文件路径（可选）

    Returns:
        转换后的JSON数据
    """
    processor = CSVTableProcessor(tables_dir)

    # 转换为JSON格式（只处理一次）
    json_data = processor.process_all_tables()

    # 如果指定了输出文件，则保存
    if output_file:
        processor.save_to_file(output_file, json_data)

    return json_data


def main():
    """主函数，用于独立运行此脚本"""
    import sys

    if len(sys.argv) < 2:
        print("使用方法: python process_tables.py <tables_directory> [output_file]")
        print("示例: python process_tables.py data/project_20250605_205528/tables output.json")
        return

    tables_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "tables_formatted.json"

    if not os.path.exists(tables_dir):
        print(f"❌ 目录不存在: {tables_dir}")
        return

    print(f"📊 开始处理表格目录: {tables_dir}")

    try:
        json_data = process_tables_in_directory(tables_dir, output_file)
        print(f"✅ 处理完成！共转换 {len(json_data) - 1} 个表格")

        # 显示转换的表格列表
        print("\n📋 转换的表格:")
        for sheet_id, sheet_data in json_data.items():
            if sheet_id != "mate":
                name = sheet_data.get('name', 'Unknown')
                rows = len(sheet_data.get('content', [])) - 1  # 减去表头行
                print(f"  • {name}: {rows} 行数据")

    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()