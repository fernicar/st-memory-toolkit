#!/usr/bin/env python3
"""
表格管理模块
负责管理CSV表格的创建、读取、更新和删除操作
"""

import pandas as pd
import logging
import os
from typing import Dict, List, Any, Optional
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入表格结构定义
from src.table_schemas import TABLE_SCHEMAS
from src.utils import get_tables_path

class TableManager:
    """表格管理器类"""

    def __init__(self, tables_dir: Optional[str] = None):
        """初始化表格管理器

        Args:
            tables_dir: 自定义表格目录路径，如果为None则使用默认路径
        """
        self.logger = logging.getLogger(__name__)
        self.tables_dir = tables_dir or get_tables_path()
        self.schemas = TABLE_SCHEMAS
        self._ensure_tables_dir()
        self._initialize_tables()

    def _ensure_tables_dir(self):
        """确保表格目录存在"""
        if not os.path.exists(self.tables_dir):
            os.makedirs(self.tables_dir)
            self.logger.info(f"创建表格目录: {self.tables_dir}")

    def _initialize_tables(self):
        """初始化所有表格文件"""
        for table_index, schema in self.schemas.items():
            file_path = os.path.join(self.tables_dir, schema['file_name'])
            if not os.path.exists(file_path):
                # 使用pandas创建空表格
                columns = [schema['columns'][i] for i in sorted(schema['columns'].keys())]
                df = pd.DataFrame(columns=columns)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                self.logger.info(f"初始化表格: {schema['name']} -> {file_path}")

    def _get_table_file_path(self, table_index: int) -> str:
        """获取表格文件路径"""
        if table_index not in self.schemas:
            raise ValueError(f"无效的表格索引: {table_index}")
        return os.path.join(self.tables_dir, self.schemas[table_index]['file_name'])

    def load_table(self, table_index: int) -> pd.DataFrame:
        """加载表格数据"""
        file_path = self._get_table_file_path(table_index)
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            return df
        except Exception as e:
            self.logger.error(f"加载表格失败 {table_index}: {e}")
            # 返回空的DataFrame
            schema = self.schemas[table_index]
            columns = [schema['columns'][i] for i in sorted(schema['columns'].keys())]
            return pd.DataFrame(columns=columns)

    def save_table(self, table_index: int, df: pd.DataFrame):
        """保存表格数据"""
        file_path = self._get_table_file_path(table_index)
        try:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"保存表格 {table_index}: {file_path}")
        except Exception as e:
            self.logger.error(f"保存表格失败 {table_index}: {e}")

    def insert_row(self, table_index: int, data: Dict[int, Any]) -> bool:
        """
        在表格中插入新行

        Args:
            table_index: 表格索引
            data: 行数据字典，键为列索引，值为单元格内容

        Returns:
            操作是否成功
        """
        try:
            df = self.load_table(table_index)
            schema = self.schemas[table_index]

            # 创建新行
            new_row = {}
            for col_index, col_name in schema['columns'].items():
                new_row[col_name] = str(data.get(col_index, ""))

            # 添加新行
            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            self.save_table(table_index, new_df)

            self.logger.info(f"插入行到表格 {table_index}: {data}")
            return True

        except Exception as e:
            self.logger.error(f"插入行失败 {table_index}: {e}")
            return False

    def delete_row(self, table_index: int, row_index: int) -> bool:
        """
        删除表格中的指定行

        Args:
            table_index: 表格索引
            row_index: 行索引

        Returns:
            操作是否成功
        """
        try:
            df = self.load_table(table_index)

            if row_index >= len(df) or row_index < 0:
                self.logger.warning(f"无效的行索引 {row_index}，表格 {table_index} 共有 {len(df)} 行")
                return False

            # 删除指定行
            df = df.drop(df.index[row_index]).reset_index(drop=True)
            self.save_table(table_index, df)

            self.logger.info(f"删除表格 {table_index} 的第 {row_index} 行")
            return True

        except Exception as e:
            self.logger.error(f"删除行失败 {table_index}, {row_index}: {e}")
            return False

    def update_row(self, table_index: int, row_index: int, data: Dict[int, Any]) -> bool:
        """
        更新表格中的指定行

        Args:
            table_index: 表格索引
            row_index: 行索引
            data: 要更新的数据字典，键为列索引，值为新内容

        Returns:
            操作是否成功
        """
        try:
            df = self.load_table(table_index)

            if row_index >= len(df) or row_index < 0:
                self.logger.warning(f"无效的行索引 {row_index}，表格 {table_index} 共有 {len(df)} 行")
                return False

            schema = self.schemas[table_index]

            # 更新指定列
            for col_index, value in data.items():
                if col_index in schema['columns']:
                    col_name = schema['columns'][col_index]
                    df.iloc[row_index, df.columns.get_loc(col_name)] = str(value)

            self.save_table(table_index, df)

            self.logger.info(f"更新表格 {table_index} 第 {row_index} 行: {data}")
            return True

        except Exception as e:
            self.logger.error(f"更新行失败 {table_index}, {row_index}: {e}")
            return False

    def get_table_content_for_prompt(self, table_index: int) -> str:
        """
        获取表格内容的格式化字符串，用于提示词

        Args:
            table_index: 表格索引

        Returns:
            格式化的表格内容字符串
        """
        try:
            df = self.load_table(table_index)
            if df.empty:
                return ""

            lines = []
            for idx, row in df.iterrows():
                row_data = [str(idx)] + [str(row[col]) for col in df.columns]
                lines.append(",".join(row_data))

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"获取表格内容失败 {table_index}: {e}")
            return ""

    def get_all_tables_content_for_prompt(self) -> str:
        """
        获取所有表格内容的格式化字符串，用于提示词

        Returns:
            所有表格内容的格式化字符串
        """
        contents = []
        for table_index in sorted(self.schemas.keys()):
            content = self.get_table_content_for_prompt(table_index)
            if content:
                contents.append(f"表格{table_index}:\n{content}")
        return "\n\n".join(contents)

    def get_table_info(self, table_index: int) -> Dict[str, Any]:
        """
        获取表格信息

        Args:
            table_index: 表格索引

        Returns:
            表格信息字典
        """
        try:
            schema = self.schemas[table_index]
            df = self.load_table(table_index)
            file_path = self._get_table_file_path(table_index)

            return {
                "name": schema['name'],
                "description": schema['description'],
                "file_path": file_path,
                "row_count": len(df),
                "column_count": len(schema['columns']),
                "columns": schema['columns']
            }

        except Exception as e:
            self.logger.error(f"获取表格信息失败 {table_index}: {e}")
            return {}

    def get_all_tables_info(self) -> Dict[int, Dict[str, Any]]:
        """
        获取所有表格的信息

        Returns:
            所有表格信息的字典
        """
        tables_info = {}
        for table_index in self.schemas.keys():
            tables_info[table_index] = self.get_table_info(table_index)
        return tables_info
