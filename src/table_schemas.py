"""
表格结构定义模块
定义系统中所有表格的结构和触发条件
"""

from typing import Dict, Any

# 表格结构定义
TABLE_SCHEMAS = {
    0: {
        "name": "时空表格",
        "description": "记录时空信息的表格，应保持在一行",
        "columns": {
            0: "日期",
            1: "时间",
            2: "地点（当前描写）",
            3: "此地角色"
        },
        "file_name": "spacetime_table.csv",
        "triggers": {
            "update": "当描写的场景，时间，人物变更时",
            "delete": "此表大于一行时应删除多余行"
        }
    },
    1: {
        "name": "角色特征表格",
        "description": "角色天生或不易改变的特征csv表格，思考本轮有否有其中的角色，他应作出什么反应",
        "columns": {
            0: "角色名",
            1: "身体特征",
            2: "性格",
            3: "职业",
            4: "爱好",
            5: "喜欢的事物（作品、虚拟人物、物品等）",
            6: "住所",
            7: "其他重要信息"
        },
        "file_name": "character_traits_table.csv",
        "triggers": {
            "insert": "当本轮出现表中没有的新角色时，应插入",
            "update": "当角色的身体出现持久性变化时，例如伤痕/当角色有新的爱好，职业，喜欢的事物时/当角色更换住所时/当角色提到重要信息时"
        }
    },
    2: {
        "name": "角色与真银铃社交表格",
        "description": "思考如果有角色和真银铃互动，应什么态度",
        "columns": {
            0: "角色名",
            1: "对真银铃关系",
            2: "对真银铃态度",
            3: "对真银铃好感"
        },
        "file_name": "social_relations_table.csv",
        "triggers": {
            "insert": "当本轮出现表中没有的新角色时，应插入",
            "update": "当角色和真银铃的交互不再符合原有的记录时/当角色和真银铃的关系改变时"
        }
    },
    3: {
        "name": "任务、命令或者约定表格",
        "description": "思考本轮是否应该执行任务/赴约",
        "columns": {
            0: "角色",
            1: "任务",
            2: "地点",
            3: "持续时间"
        },
        "file_name": "tasks_table.csv",
        "triggers": {
            "insert": "当特定时间约定一起去做某事时/某角色收到做某事的命令或任务时",
            "delete": "当大家赴约时/任务或命令完成时/任务，命令或约定被取消时"
        }
    },
    4: {
        "name": "重要事件历史表格",
        "description": "记录真银铃或角色经历的重要事件",
        "columns": {
            0: "角色",
            1: "事件简述",
            2: "日期",
            3: "地点",
            4: "情绪"
        },
        "file_name": "important_events_table.csv",
        "triggers": {
            "insert": "当某个角色经历让自己印象深刻的事件时，比如表白、分手等"
        }
    },
    5: {
        "name": "重要物品表格",
        "description": "对某人很贵重或有特殊纪念意义的物品",
        "columns": {
            0: "拥有人",
            1: "物品描述",
            2: "物品名",
            3: "重要原因"
        },
        "file_name": "important_items_table.csv",
        "triggers": {
            "insert": "当某人获得了贵重或有特殊意义的物品时/当某个已有物品有了特殊意义时"
        }
    }
}

def get_table_schema(table_index: int) -> Dict[str, Any]:
    """
    获取指定表格的结构定义

    Args:
        table_index: 表格索引

    Returns:
        表格结构字典
    """
    return TABLE_SCHEMAS.get(table_index, {})

def get_all_table_schemas() -> Dict[int, Dict[str, Any]]:
    """
    获取所有表格的结构定义

    Returns:
        所有表格结构字典
    """
    return TABLE_SCHEMAS.copy()

def get_table_file_name(table_index: int) -> str:
    """
    获取表格文件名

    Args:
        table_index: 表格索引

    Returns:
        CSV文件名
    """
    schema = get_table_schema(table_index)
    return schema.get("file_name", f"table_{table_index}.csv")