# SillyTavern Tavern Memory Import Tool 📚✨

## 🎯 Project Overview

This project is a companion script tool for the **[SillyTavern Tavern Memory Enhancement Plugin](https://github.com/muyoou/st-memory-enhancement)**, designed to solve the problems of **chat log migration** and **table memory compression**.

### 💡 Core Problems Solved

**Have you ever encountered these problems?**

1.  **Chat Log Migration**: After having many valuable conversations on official websites (like ChatGPT, Claude, etc.) or other chat software, you want to migrate these precious chat logs to **SillyTavern** to continue using them.
2.  **Memory Table Compression**: After long-term use, the tavern memory table data becomes too large and needs to be intelligently compressed and organized to improve efficiency. However, the built-in reconstruction function of the plugin is sometimes unstable.

**This tool was born for this!** 🚀

### 🔄 How It Works

#### 📖 Chat to Table Mode (chat_to_table.py)
1.  **Import Conversations**: Import external chat logs into standard JSON format.
2.  **Intelligent Analysis**: Use the Google Gemini API to analyze the conversation content.
3.  **Automatic Table Creation**: Automatically generate memory data based on the table structure of the [Tavern Memory Enhancement Plugin](https://github.com/muyoou/st-memory-enhancement).
4.  **Formatted Output**: Generate a compatible JSON format that can be directly imported into the tavern memory plugin.

#### 🗜️ Table Compression Mode (table_compression.py)
1.  **Data Loading**: Load existing memory table data (supports CSV and JSON formats).
2.  **Batch Processing**: Intelligently process large tables in batches to avoid processing too much data at once.
3.  **Overlapping Compression**: Use overlapping batches to ensure data integrity and context continuity.
4.  **Intelligent Integration**: Analyze and merge duplicate, similar, or redundant memory entries through LLM.
5.  **Efficient Output**: Generate compressed tables and JSON format files.

---

## 🛠️ Project Structure

```
memory_table/
├── data/                           # Data directory
│   ├── chat.json                  # Conversation data file (for chat to table)
│   ├── table_data.json           # Table data file (for table compression, optional)
│   └── tables/                   # Existing table file directory (for table compression)
├── result/                         # Processing results directory
│   ├── chat_to_table/             # Chat to table results
│   └── table_compression/         # Table compression results
├── src/                           # Source code directory
│   ├── table_manager.py          # Table manager
│   ├── conversation_processor.py # Conversation processor
│   ├── prompt_manager.py         # Prompt manager
│   ├── llm_client.py             # Google Gemini API client
│   ├── table_converter.py        # Table conversion processor (generates tavern format)
│   ├── table_schemas.py          # Table schema definitions
│   └── utils.py                  # Utility functions
├── config.py                     # Configuration file
├── chat_to_table.py              # Chat to table main program
├── table_compression.py          # Table compression main program
├── prompt.py                     # Prompt file
├── requirements.txt              # Project dependencies
└── README.md                     # Project description
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Set your Google Gemini API key in `config.py`:
```python
# Supports multiple API key rotation to avoid high frequency usage of a single key
GEMINI_API_KEYS = [
    "your_first_api_key_here",
    "your_second_api_key_here",
    # You can add more API keys
]
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

# Table compression configuration
BATCH_SIZE = 50         # Batch processing size
OVERLAP_SIZE = 5        # Overlap size (number of overlapping rows between adjacent batches)
```

### 3A. How to Use Chat to Table Mode

#### Prepare Chat Data
Organize your chat logs into JSON format and put them in `data/chat.json`:
```json
[
    {"role": "user", "content": "User message content"},
    {"role": "assistant", "content": "AI reply content"},
    ...
]
```

#### Run the Conversion Program
```bash
python chat_to_table.py
```

### 3B. How to Use Table Compression Mode

#### Prepare Table Data
Put the table files to be compressed into the `data/tables/` directory, or organize the table data into JSON format and put it in `data/table_data.json`:

#### Run the Compression Program
```bash
python table_compression.py
```

The program will:
1.  Automatically back up the original table data.
2.  Intelligently process large tables in batches (default 50 rows per batch, 5 overlapping rows).
3.  Call the AI for duplicate data identification and content integration.
4.  Generate compressed tables and JSON export files.
5.  Provide compression statistics and detailed logs.

### 4. Import to SillyTavern
Import the generated `result/*/tables_formatted.json` file into the [SillyTavern Tavern Memory Enhancement Plugin](https://github.com/muyoou/st-memory-enhancement)!

## ⚙️ Configuration Description

### API Configuration
- `GEMINI_API_KEYS`: A list of Google Gemini API keys (supports multiple key rotation).
- `GEMINI_MODEL`: The model version to use.
- `MAX_CONTEXT_LENGTH`: The maximum context length (default 49).

### Table Compression Configuration
- `BATCH_SIZE`: The number of rows per batch during batch processing (default 50).
- `OVERLAP_SIZE`: The number of overlapping rows between adjacent batches (default 5).
- `TARGET_TABLE_INDEX`: The index of the main target table for compression (default 4, i.e., the important events table, please change the prompt yourself to compress other tables).

### Path Configuration
- `DATA_ROOT_DIR`: The data root directory (default "data").
- `OUTPUT_ROOT_DIR`: The output root directory (default "result").
- `CHAT_TO_TABLE_OUTPUT_DIR`: The chat to table output directory.
- `TABLE_COMPRESSION_OUTPUT_DIR`: The table compression output directory.

### Table Structure
All table structures follow the specifications of the Tavern Memory Enhancement Plugin to ensure perfect compatibility.

---

## 🔗 Related Links

- **[SillyTavern Tavern Memory Enhancement Plugin](https://github.com/muyoou/st-memory-enhancement)** - The companion plugin for this tool.
- **[SillyTavern Official Project](https://github.com/SillyTavern/SillyTavern)** - The AI role-playing chat platform.



---

## ⚠️ Notes

### General Notes
1.  **Import Notice**: You must have had at least one conversation in the current chat before importing the table, otherwise you will get an error "no record carrier" or the memory cannot be read.
2.  **API Quota Management**: Large table compression will consume a large number of API calls, it is recommended to configure multiple API keys.
3.  **Version Compatibility**: It is recommended to use version V2.0.3 of the Tavern Memory Enhancement Plugin, subsequent versions may not be compatible.

---

## 🤝 Contribution and Support

Issues and Pull Requests are welcome! If this tool is helpful to you, please consider:
- ⭐ Starring the project
- 🔄 Sharing with more tavern users
- 💬 Exchanging usage experiences in the Tavern Memory Enhancement Plugin community

**Let's make the tavern's memory more intelligent and efficient together!** ✨