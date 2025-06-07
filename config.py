#!/usr/bin/env python3
"""
配置管理模块
"""

import os
import logging

# ===================
# API配置
# ===================

# Gemini API配置
# 支持多个API key轮换使用，避免单个key使用频率过高
GEMINI_API_KEYS = [
]

GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
# GEMINI_MODEL = "gemini-2.0-flash"
# GEMINI_MODEL = "gemini-2.0-flash-lite"

# ===================
# 穿甲增强(慎开)
# ===================
BYPASS_ENHANCEMENT = True  # 是否开启穿甲增强

# ===================
# 表格生成配置
# ===================

# 上下文长度限制
MAX_CONTEXT_LENGTH = 49  # 最大上下文长度，包括历史对话和当前用户输入

# ===================
# 表格压缩配置
# ===================

# 批处理大小
BATCH_SIZE = 50

# 重叠大小（相邻批次之间的重叠行数）
OVERLAP_SIZE = 5

# ===================
# 项目路径配置
# ===================

# 指定项目文件夹路径（如果为空或不存在，将在data目录下创建新文件夹）
PROJECT_DIR_PATH = ""  # 设置为空，将自动创建新的时间戳文件夹

# 数据根目录
DATA_ROOT_DIR = "data"

# 当前项目文件夹（动态设置）
CURRENT_PROJECT_FOLDER = ""

# ===================
# 输入输出路径配置
# ===================

# 输入文件路径
INPUT_CHAT_FILE = os.path.join(DATA_ROOT_DIR, "chat.json")  # 输入聊天文件
INPUT_TABLES_DIR = os.path.join(DATA_ROOT_DIR, "tables")  # 输入表格目录

# 输出根目录
OUTPUT_ROOT_DIR = "result"

# 不同模块的输出目录
CHAT_TO_TABLE_OUTPUT_DIR = os.path.join(OUTPUT_ROOT_DIR, "chat_to_table")
TABLE_COMPRESSION_OUTPUT_DIR = os.path.join(OUTPUT_ROOT_DIR, "table_compression")

# ===================
# 日志配置
# ===================

LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
