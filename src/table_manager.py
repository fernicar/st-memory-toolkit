#!/usr/bin/env python3
"""
Table management module
Responsible for creating, reading, updating, and deleting CSV tables
"""

import pandas as pd
import logging
import os
from typing import Dict, List, Any, Optional
import sys

# Add the project root directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import table schema definitions
from src.table_schemas import TABLE_SCHEMAS
from src.utils import get_tables_path

class TableManager:
    """Table manager class"""

    def __init__(self, tables_dir: Optional[str] = None):
        """Initializes the table manager

        Args:
            tables_dir: Custom table directory path, if None, the default path is used
        """
        self.logger = logging.getLogger(__name__)
        self.tables_dir = tables_dir or get_tables_path()
        self.schemas = TABLE_SCHEMAS
        self._ensure_tables_dir()
        self._initialize_tables()

    def _ensure_tables_dir(self):
        """Ensures the table directory exists"""
        if not os.path.exists(self.tables_dir):
            os.makedirs(self.tables_dir)
            self.logger.info(f"Created table directory: {self.tables_dir}")

    def _initialize_tables(self):
        """Initializes all table files"""
        for table_index, schema in self.schemas.items():
            file_path = os.path.join(self.tables_dir, schema['file_name'])
            if not os.path.exists(file_path):
                # Use pandas to create an empty table
                columns = [schema['columns'][i] for i in sorted(schema['columns'].keys())]
                df = pd.DataFrame(columns=columns)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                self.logger.info(f"Initialized table: {schema['name']} -> {file_path}")

    def _get_table_file_path(self, table_index: int) -> str:
        """Gets the table file path"""
        if table_index not in self.schemas:
            raise ValueError(f"Invalid table index: {table_index}")
        return os.path.join(self.tables_dir, self.schemas[table_index]['file_name'])

    def load_table(self, table_index: int) -> pd.DataFrame:
        """Loads table data"""
        file_path = self._get_table_file_path(table_index)
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            return df
        except Exception as e:
            self.logger.error(f"Failed to load table {table_index}: {e}")
            # Return an empty DataFrame
            schema = self.schemas[table_index]
            columns = [schema['columns'][i] for i in sorted(schema['columns'].keys())]
            return pd.DataFrame(columns=columns)

    def save_table(self, table_index: int, df: pd.DataFrame):
        """Saves table data"""
        file_path = self._get_table_file_path(table_index)
        try:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"Saved table {table_index}: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save table {table_index}: {e}")

    def insert_row(self, table_index: int, data: Dict[int, Any]) -> bool:
        """
        Inserts a new row into the table

        Args:
            table_index: The table index
            data: A dictionary of row data, where the key is the column index and the value is the cell content

        Returns:
            Whether the operation was successful
        """
        try:
            df = self.load_table(table_index)
            schema = self.schemas[table_index]

            # Create a new row
            new_row = {}
            for col_index, col_name in schema['columns'].items():
                new_row[col_name] = str(data.get(col_index, ""))

            # Add the new row
            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            self.save_table(table_index, new_df)

            self.logger.info(f"Inserted row into table {table_index}: {data}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to insert row {table_index}: {e}")
            return False

    def delete_row(self, table_index: int, row_index: int) -> bool:
        """
        Deletes a specified row from the table

        Args:
            table_index: The table index
            row_index: The row index

        Returns:
            Whether the operation was successful
        """
        try:
            df = self.load_table(table_index)

            if row_index >= len(df) or row_index < 0:
                self.logger.warning(f"Invalid row index {row_index}, table {table_index} has {len(df)} rows")
                return False

            # Delete the specified row
            df = df.drop(df.index[row_index]).reset_index(drop=True)
            self.save_table(table_index, df)

            self.logger.info(f"Deleted row {row_index} from table {table_index}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete row {table_index}, {row_index}: {e}")
            return False

    def update_row(self, table_index: int, row_index: int, data: Dict[int, Any]) -> bool:
        """
        Updates a specified row in the table

        Args:
            table_index: The table index
            row_index: The row index
            data: A dictionary of data to update, where the key is the column index and the value is the new content

        Returns:
            Whether the operation was successful
        """
        try:
            df = self.load_table(table_index)

            if row_index >= len(df) or row_index < 0:
                self.logger.warning(f"Invalid row index {row_index}, table {table_index} has {len(df)} rows")
                return False

            schema = self.schemas[table_index]

            # Update the specified columns
            for col_index, value in data.items():
                if col_index in schema['columns']:
                    col_name = schema['columns'][col_index]
                    df.iloc[row_index, df.columns.get_loc(col_name)] = str(value)

            self.save_table(table_index, df)

            self.logger.info(f"Updated row {row_index} in table {table_index}: {data}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update row {table_index}, {row_index}: {e}")
            return False

    def get_table_content_for_prompt(self, table_index: int) -> str:
        """
        Gets a formatted string of the table content for a prompt

        Args:
            table_index: The table index

        Returns:
            A formatted string of the table content
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
            self.logger.error(f"Failed to get table content {table_index}: {e}")
            return ""

    def get_all_tables_content_for_prompt(self) -> str:
        """
        Gets a formatted string of all table content for a prompt

        Returns:
            A formatted string of all table content
        """
        contents = []
        for table_index in sorted(self.schemas.keys()):
            content = self.get_table_content_for_prompt(table_index)
            if content:
                contents.append(f"Table{table_index}:\n{content}")
        return "\n\n".join(contents)

    def get_table_info(self, table_index: int) -> Dict[str, Any]:
        """
        Gets table information

        Args:
            table_index: The table index

        Returns:
            A dictionary of table information
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
            self.logger.error(f"Failed to get table information {table_index}: {e}")
            return {}

    def get_all_tables_info(self) -> Dict[int, Dict[str, Any]]:
        """
        Gets information for all tables

        Returns:
            A dictionary of all table information
        """
        tables_info = {}
        for table_index in self.schemas.keys():
            tables_info[table_index] = self.get_table_info(table_index)
        return tables_info
