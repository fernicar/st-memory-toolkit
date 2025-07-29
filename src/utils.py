#!/usr/bin/env python3
"""
Utility functions module
Contains project path management and other helper functions
"""

import os
from datetime import datetime

# Import configuration constants
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_ROOT_DIR, PROJECT_DIR_PATH, CURRENT_PROJECT_FOLDER


def ensure_project_directories():
    """Ensures the project directory structure exists"""
    project_path = get_project_path()
    tables_path = get_tables_path()

    os.makedirs(project_path, exist_ok=True)
    os.makedirs(tables_path, exist_ok=True)

    return project_path, tables_path


def list_available_projects():
    """Lists available projects"""
    if not os.path.exists(DATA_ROOT_DIR):
        return []

    projects = []
    for item in os.listdir(DATA_ROOT_DIR):
        item_path = os.path.join(DATA_ROOT_DIR, item)
        if os.path.isdir(item_path) and item.startswith("project_"):
            projects.append(item)

    return sorted(projects, reverse=True)  # Newest first


def get_project_folder():
    """Gets the project folder name"""
    import config

    # If a specific path is specified
    if PROJECT_DIR_PATH and os.path.exists(PROJECT_DIR_PATH):
        # Extract the folder name from the path
        config.CURRENT_PROJECT_FOLDER = os.path.basename(PROJECT_DIR_PATH.rstrip(os.sep))
        return config.CURRENT_PROJECT_FOLDER

    # If no path is specified or the path does not exist, create a new timestamped folder
    if not config.CURRENT_PROJECT_FOLDER:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config.CURRENT_PROJECT_FOLDER = f"project_{timestamp}"

    return config.CURRENT_PROJECT_FOLDER


def get_project_path():
    """Gets the full project path"""
    # If a specific path is specified and it exists, use it directly
    if PROJECT_DIR_PATH and os.path.exists(PROJECT_DIR_PATH):
        return PROJECT_DIR_PATH

    # Otherwise, use the folder name in the data directory
    return os.path.join(DATA_ROOT_DIR, get_project_folder())


def get_tables_path():
    """Gets the tables folder path"""
    return os.path.join(get_project_path(), "tables")


def get_chat_file_path():
    """Gets the chat file path"""
    return os.path.join(get_project_path(), "chat.json")


# ===================
# New: Input/output path management functions
# ===================

def get_input_chat_file():
    """Gets the input chat file path"""
    from config import INPUT_CHAT_FILE
    return INPUT_CHAT_FILE


def get_input_tables_dir():
    """Gets the input tables directory path"""
    from config import INPUT_TABLES_DIR
    return INPUT_TABLES_DIR


def ensure_output_directories(output_type: str):
    """
    Ensures the output directories exist

    Args:
        output_type: The output type, can be "chat_to_table" or "table_compression"

    Returns:
        tuple: (output directory path, tables subdirectory path)
    """
    from config import OUTPUT_ROOT_DIR

    # Create a timestamped project folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_folder = f"project_{timestamp}"

    # Build the output path
    output_path = os.path.join(OUTPUT_ROOT_DIR, output_type, project_folder)
    tables_path = os.path.join(output_path, "tables")

    # Ensure the directories exist
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(tables_path, exist_ok=True)

    return output_path, tables_path
