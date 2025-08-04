#!/usr/bin/env python3
"""
Configuration management module
"""

import os
import logging

# ===================
# API Configuration
# ===================

# Gemini API configuration
# Supports multiple API key rotation to avoid high frequency usage of a single key
GEMINI_API_KEYS = [
]

GEMINI_MODEL = "gemini-2.5-flash-lite"
# GEMINI_MODEL = "gemini-2.5-flash"
# GEMINI_MODEL = "gemini-2.5-flash-lite"

# ===================
# Bypass Enhancement (Use with caution)
# ===================
BYPASS_ENHANCEMENT = True  # Whether to enable bypass enhancement

# ===================
# Table Generation Configuration
# ===================

# Context length limit
MAX_CONTEXT_LENGTH = 49  # Maximum context length, including historical conversation and current user input

# ===================
# Table Compression Configuration
# ===================

# Batch size
BATCH_SIZE = 50

# Overlap size (number of overlapping rows between adjacent batches)
OVERLAP_SIZE = 5

# ===================
# Project Path Configuration
# ===================

# Specify the project folder path (if empty or non-existent, a new folder will be created in the data directory)
PROJECT_DIR_PATH = ""  # Set to empty to automatically create a new timestamped folder

# Data root directory
DATA_ROOT_DIR = "data"

# Current project folder (dynamically set)
CURRENT_PROJECT_FOLDER = ""

# ===================
# Input/Output Path Configuration
# ===================

# Input file paths
INPUT_CHAT_FILE = os.path.join(DATA_ROOT_DIR, "chat.json")  # Input chat file
INPUT_TABLES_DIR = os.path.join(DATA_ROOT_DIR, "tables")  # Input tables directory

# Output root directory
OUTPUT_ROOT_DIR = "result"

# Output directories for different modules
CHAT_TO_TABLE_OUTPUT_DIR = os.path.join(OUTPUT_ROOT_DIR, "chat_to_table")
TABLE_COMPRESSION_OUTPUT_DIR = os.path.join(OUTPUT_ROOT_DIR, "table_compression")

# ===================
# Logging Configuration
# ===================

LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
