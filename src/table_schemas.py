"""
Table schema definition module
Defines the structure and trigger conditions for all tables in the system
"""

from typing import Dict, Any

# Table schema definitions
TABLE_SCHEMAS = {
    0: {
        "name": "Spacetime Table",
        "description": "Table for recording spacetime information, should be kept to one row",
        "columns": {
            0: "Date",
            1: "Time",
            2: "Location (Current)",
            3: "Characters Present"
        },
        "file_name": "spacetime_table.csv",
        "triggers": {
            "update": "When the scene, time, or characters change",
            "delete": "If this table has more than one row, the extra rows should be deleted"
        }
    },
    1: {
        "name": "Character Traits Table",
        "description": "A CSV table of innate or hard-to-change character traits. Consider if any of these characters are in this round and how they should react.",
        "columns": {
            0: "Character Name",
            1: "Physical Traits",
            2: "Personality",
            3: "Occupation",
            4: "Hobbies",
            5: "Favorite Things (Works, Fictional Characters, Items, etc.)",
            6: "Residence",
            7: "Other Important Information"
        },
        "file_name": "character_traits_table.csv",
        "triggers": {
            "insert": "When a new character not in the table appears in this round, they should be inserted",
            "update": "When a character's body undergoes a lasting change, such as a scar / when a character has a new hobby, profession, or favorite thing / when a character changes residence / when a character mentions important information"
        }
    },
    2: {
        "name": "Character and <user> Social Table",
        "description": "Consider what attitude a character should have if they interact with <user>",
        "columns": {
            0: "Character Name",
            1: "Relationship with <user>",
            2: "Attitude towards <user>",
            3: "Affection towards <user>"
        },
        "file_name": "social_relations_table.csv",
        "triggers": {
            "insert": "When a new character not in the table appears in this round, they should be inserted",
            "update": "When a character's interaction with <user> no longer matches the original record / when a character's relationship with <user> changes"
        }
    },
    3: {
        "name": "Tasks, Commands, or Agreements Table",
        "description": "Consider whether a task should be performed or an appointment kept in this round",
        "columns": {
            0: "Character",
            1: "Task",
            2: "Location",
            3: "Duration"
        },
        "file_name": "tasks_table.csv",
        "triggers": {
            "insert": "When an agreement is made to do something at a specific time / when a character receives a command or task to do something",
            "delete": "When everyone keeps an appointment / when a task or command is completed / when a task, command, or agreement is canceled"
        }
    },
    4: {
        "name": "Important Events History Table",
        "description": "Records important events experienced by <user> or characters",
        "columns": {
            0: "Character",
            1: "Event Summary",
            2: "Date",
            3: "Location",
            4: "Emotion"
        },
        "file_name": "important_events_table.csv",
        "triggers": {
            "insert": "When a character experiences a memorable event, such as a confession, breakup, etc."
        }
    },
    5: {
        "name": "Important Items Table",
        "description": "Items that are very valuable to someone or have special sentimental value",
        "columns": {
            0: "Owner",
            1: "Item Description",
            2: "Item Name",
            3: "Reason for Importance"
        },
        "file_name": "important_items_table.csv",
        "triggers": {
            "insert": "When someone obtains a valuable or meaningful item / when an existing item gains special meaning"
        }
    }
}

def get_table_schema(table_index: int) -> Dict[str, Any]:
    """
    Gets the schema definition for a specified table

    Args:
        table_index: The table index

    Returns:
        A dictionary of the table schema
    """
    return TABLE_SCHEMAS.get(table_index, {})

def get_all_table_schemas() -> Dict[int, Dict[str, Any]]:
    """
    Gets the schema definitions for all tables

    Returns:
        A dictionary of all table schemas
    """
    return TABLE_SCHEMAS.copy()

def get_table_file_name(table_index: int) -> str:
    """
    Gets the table file name

    Args:
        table_index: The table index

    Returns:
        The CSV file name
    """
    schema = get_table_schema(table_index)
    return schema.get("file_name", f"table_{table_index}.csv")