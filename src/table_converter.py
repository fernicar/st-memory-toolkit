#!/usr/bin/env python3
"""
Table processing script - converts CSV table files to the specified JSON format
"""

import os
import csv
import json
import uuid
from typing import Dict, Any, List


class CSVTableConverter:
    """CSV Table Converter"""

    def __init__(self, tables_dir: str):
        self.tables_dir = tables_dir

        # Table configuration mapping
        self.table_configs = {
            "spacetime_table.csv": {
                "name": "Spacetime Table",
                "note": "Table for recording spacetime information, should be kept to one row",
                "initNode": "This round needs to record the current time, location, and character information, use the insertRow function",
                "deleteNode": "If this table has more than one row, the extra rows should be deleted",
                "updateNode": "When the scene, time, or characters change",
                "required": True
            },
            "character_traits_table.csv": {
                "name": "Character Traits Table",
                "note": "A CSV table of innate or hard-to-change character traits. Consider if any of these characters are in this round and how they should react.",
                "initNode": "This round must find all known characters from the text above and insert them using insertRow, character name cannot be empty",
                "deleteNode": "",
                "updateNode": "When a character's body undergoes a lasting change, such as a scar / when a character has a new hobby, profession, or favorite thing / when a character changes residence / when a character mentions important information",
                "insertNode": "When a new character not in the table appears in this round, they should be inserted",
                "required": True
            },
            "social_relations_table.csv": {
                "name": "Character and <user> Social Table",
                "note": "Consider what attitude a character should have if they interact with <user>",
                "initNode": "This round must find all known characters from the text above and insert them using insertRow, character name cannot be empty",
                "deleteNode": "",
                "updateNode": "When a character's interaction with <user> no longer matches the original record / when a character's relationship with <user> changes",
                "insertNode": "When a new character not in the table appears in this round, they should be inserted",
                "required": True
            },
            "tasks_table.csv": {
                "name": "Tasks, Commands, or Agreements Table",
                "note": "Consider whether a task should be performed or an appointment kept in this round",
                "initNode": "",
                "deleteNode": "When everyone keeps an appointment / when a task or command is completed / when a task, command, or agreement is canceled",
                "updateNode": "",
                "insertNode": "When an agreement is made to do something at a specific time / when a character receives a command or task to do something",
                "required": False
            },
            "important_events_table.csv": {
                "name": "Important Events History Table",
                "note": "Records important events experienced by <user> or characters",
                "initNode": "This round must find insertable events from the text above and insert them using insertRow",
                "deleteNode": "",
                "updateNode": "",
                "insertNode": "When a character experiences a memorable event, such as a confession, breakup, etc.",
                "required": True
            },
            "important_items_table.csv": {
                "name": "Important Items Table",
                "note": "Items that are very valuable to someone or have special sentimental value",
                "initNode": "",
                "deleteNode": "",
                "updateNode": "",
                "insertNode": "When someone obtains a valuable or meaningful item / when an existing item gains special meaning",
                "required": False
            }
        }

    def generate_sheet_uid(self) -> str:
        """Generates a unique identifier for a sheet"""
        return f"sheet_{uuid.uuid4().hex[:8]}"

    def read_csv_file(self, file_path: str) -> List[List]:
        """Reads a CSV file and returns its content as an array"""
        content = []

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)

                if not rows:
                    return content

                # Get the filename
                file_name = os.path.basename(file_path)

                # Add the header row, with null in the first column
                header = [None] + rows[0]

                # Correct the header of the social table
                if file_name == "social_relations_table.csv" and len(header) > 1:
                    # Replace "真银铃" with "<user>" in the header
                    for i in range(1, len(header)):
                        if header[i] and "真银铃" in header[i]:
                            header[i] = header[i].replace("真银铃", "<user>")

                content.append(header)

                # Add data rows, with null in the first column
                for row in rows[1:]:
                    if row:  # Skip empty rows
                        data_row = [None] + row
                        content.append(data_row)

        except Exception as e:
            print(f"Failed to read CSV file {file_path}: {e}")

        return content

    def create_sheet_config(self, file_name: str, content: List[List]) -> Dict[str, Any]:
        """Creates the configuration for a single table"""
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
                    "Custom Style": {
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
        """Processes all table files and generates JSON format"""
        result = {}

        # Process all CSV files
        for file_name in self.table_configs.keys():
            file_path = os.path.join(self.tables_dir, file_name)

            if os.path.exists(file_path):
                print(f"Processing file: {file_name}")
                content = self.read_csv_file(file_path)

                if not content:
                    # If the file is empty, create content with only the header
                    if file_name == "spacetime_table.csv":
                        content = [[None, "Date", "Time", "Location (Current)", "Characters Present"]]
                    elif file_name == "character_traits_table.csv":
                        content = [[None, "Character Name", "Physical Traits", "Personality", "Occupation", "Hobbies", "Favorite Things (Works, Fictional Characters, Items, etc.)", "Residence", "Other Important Information"]]
                    elif file_name == "social_relations_table.csv":
                        content = [[None, "Character Name", "Relationship with <user>", "Attitude towards <user>", "Affection towards <user>"]]
                    elif file_name == "tasks_table.csv":
                        content = [[None, "Character", "Task", "Location", "Duration"]]
                    elif file_name == "important_events_table.csv":
                        content = [[None, "Character", "Event Summary", "Date", "Location", "Emotion"]]
                    elif file_name == "important_items_table.csv":
                        content = [[None, "Owner", "Item Description", "Item Name", "Reason for Importance"]]

                sheet_config = self.create_sheet_config(file_name, content)
                result[sheet_config["uid"]] = sheet_config
            else:
                print(f"File not found: {file_path}")

        # Add mate information
        result["mate"] = {
            "type": "chatSheets",
            "version": 1
        }

        return result

    def save_to_file(self, output_file: str, json_data: Dict[str, Any]) -> bool:
        """Saves JSON data to a file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            print(f"✅ Table data saved to: {output_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to save file: {e}")
            return False


def process_tables_in_directory(tables_dir: str, output_file: str = None) -> Dict[str, Any]:
    """
    Processes table files in a specified directory

    Args:
        tables_dir: The path to the tables directory
        output_file: The path to the output file (optional)

    Returns:
        The converted JSON data
    """
    processor = CSVTableConverter(tables_dir)

    # Convert to JSON format (only process once)
    json_data = processor.process_all_tables()

    # If an output file is specified, save it
    if output_file:
        processor.save_to_file(output_file, json_data)

    return json_data


def main():
    """Main function, for running this script independently"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python table_converter.py <tables_directory> [output_file]")
        print("Example: python table_converter.py data/project_20250605_205528/tables output.json")
        return

    tables_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "tables_formatted.json"

    if not os.path.exists(tables_dir):
        print(f"❌ Directory not found: {tables_dir}")
        return

    print(f"📊 Starting to process table directory: {tables_dir}")

    try:
        json_data = process_tables_in_directory(tables_dir, output_file)
        print(f"✅ Processing complete! Converted {len(json_data) - 1} tables")

        # Display the list of converted tables
        print("\n📋 Converted tables:")
        for sheet_id, sheet_data in json_data.items():
            if sheet_id != "mate":
                name = sheet_data.get('name', 'Unknown')
                rows = len(sheet_data.get('content', [])) - 1  # Subtract the header row
                print(f"  • {name}: {rows} rows of data")

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()