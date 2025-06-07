#!/usr/bin/env python3
"""
工具函数模块
包含项目路径管理和其他辅助功能
"""

import os
from datetime import datetime

# 导入配置常量
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_ROOT_DIR, PROJECT_DIR_PATH, CURRENT_PROJECT_FOLDER


def ensure_project_directories():
    """确保项目目录结构存在"""
    project_path = get_project_path()
    tables_path = get_tables_path()

    os.makedirs(project_path, exist_ok=True)
    os.makedirs(tables_path, exist_ok=True)

    return project_path, tables_path


def list_available_projects():
    """列出可用的项目"""
    if not os.path.exists(DATA_ROOT_DIR):
        return []

    projects = []
    for item in os.listdir(DATA_ROOT_DIR):
        item_path = os.path.join(DATA_ROOT_DIR, item)
        if os.path.isdir(item_path) and item.startswith("project_"):
            projects.append(item)

    return sorted(projects, reverse=True)  # 最新的在前面


def get_project_folder():
    """获取项目文件夹名"""
    import config

    # 如果指定了具体路径
    if PROJECT_DIR_PATH and os.path.exists(PROJECT_DIR_PATH):
        # 从路径中提取文件夹名
        config.CURRENT_PROJECT_FOLDER = os.path.basename(PROJECT_DIR_PATH.rstrip(os.sep))
        return config.CURRENT_PROJECT_FOLDER

    # 如果没有指定路径或路径不存在，创建新的时间戳文件夹
    if not config.CURRENT_PROJECT_FOLDER:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config.CURRENT_PROJECT_FOLDER = f"project_{timestamp}"

    return config.CURRENT_PROJECT_FOLDER


def get_project_path():
    """获取项目完整路径"""
    # 如果指定了具体路径且存在，直接使用
    if PROJECT_DIR_PATH and os.path.exists(PROJECT_DIR_PATH):
        return PROJECT_DIR_PATH

    # 否则在data目录下使用文件夹名
    return os.path.join(DATA_ROOT_DIR, get_project_folder())


def get_tables_path():
    """获取表格文件夹路径"""
    return os.path.join(get_project_path(), "tables")


def get_chat_file_path():
    """获取聊天文件路径"""
    return os.path.join(get_project_path(), "chat.json")


# ===================
# 新增：输入输出路径管理函数
# ===================

def get_input_chat_file():
    """获取输入聊天文件路径"""
    from config import INPUT_CHAT_FILE
    return INPUT_CHAT_FILE


def get_input_tables_dir():
    """获取输入表格目录路径"""
    from config import INPUT_TABLES_DIR
    return INPUT_TABLES_DIR


def ensure_output_directories(output_type: str):
    """
    确保输出目录存在

    Args:
        output_type: 输出类型，可以是 "chat_to_table" 或 "table_compression"

    Returns:
        tuple: (输出目录路径, 表格子目录路径)
    """
    from config import OUTPUT_ROOT_DIR

    # 创建带时间戳的项目文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_folder = f"project_{timestamp}"

    # 构建输出路径
    output_path = os.path.join(OUTPUT_ROOT_DIR, output_type, project_folder)
    tables_path = os.path.join(output_path, "tables")

    # 确保目录存在
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(tables_path, exist_ok=True)

    return output_path, tables_path
