# SillyTavern 酒馆记忆导入工具 📚✨

## 🎯 项目概述

本项目是 **[SillyTavern 酒馆记忆增强插件](https://github.com/muyoou/st-memory-enhancement)** 的配套脚本工具，专为解决 **聊天记录迁移** 和 **表格记忆压缩** 问题而设计。

### 💡 解决的核心问题

**你是否遇到过这样的困扰？**

1. **聊天记录迁移**: 在官网（如ChatGPT、Claude等）或其他聊天软件中进行了大量有价值的对话，想要将这些珍贵的聊天记录迁移到 **SillyTavern酒馆** 中继续使用
2. **记忆表格压缩**: 经过长时间使用后，酒馆记忆表格数据过于庞大，需要智能化压缩和整理以提高效率。但插件内置的重构功能有时不稳定。

**本工具正是为此而生！** 🚀

### 🔄 工作原理

#### 📖 聊天转表格模式（chat_to_table.py）
1. **导入对话**: 将外部聊天记录导入为标准JSON格式
2. **智能分析**: 使用Google Gemini API分析对话内容
3. **自动建表**: 基于 [酒馆记忆增强插件](https://github.com/muyoou/st-memory-enhancement) 的表格结构自动生成记忆数据
4. **格式输出**: 生成compatible的JSON格式，可直接导入酒馆记忆插件

#### 🗜️ 表格压缩模式（table_compression.py）
1. **数据载入**: 载入现有的记忆表格数据（支持CSV和JSON格式）
2. **分批处理**: 智能分批处理大型表格，避免单次处理数据过多
3. **重叠压缩**: 使用重叠批次确保数据完整性和上下文连贯性
4. **智能整合**: 通过LLM分析合并重复、相似或冗余的记忆条目
5. **高效输出**: 生成压缩后的表格和JSON格式文件

---

## 🛠️ 项目结构

```
memory_table/
├── data/                           # 数据目录
│   ├── chat.json                  # 对话数据文件（用于聊天转表格）
│   ├── table_data.json           # 表格数据文件（用于表格压缩，可选）
│   └── tables/                   # 现有表格文件目录（用于表格压缩）
├── result/                         # 处理结果目录
│   ├── chat_to_table/             # 聊天转表格结果
│   └── table_compression/         # 表格压缩结果
├── src/                           # 源代码目录
│   ├── table_manager.py          # 表格管理器
│   ├── chat_processor.py         # 对话处理器
│   ├── prompt_handler.py         # 提示词处理器
│   ├── llm_client.py             # Google Gemini API客户端
│   ├── process_tables.py         # 表格转换处理器（生成酒馆格式）
│   ├── table_schemas.py          # 表格结构定义
│   └── utils.py                  # 工具函数
├── config.py                     # 配置文件
├── chat_to_table.py              # 聊天转表格主程序
├── table_compression.py          # 表格压缩主程序
├── prompt.py                     # 提示词文件
├── requirements.txt              # 项目依赖
└── README.md                     # 项目说明
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
在 `config.py` 中设置您的Google Gemini API密钥：
```python
# 支持多个API key轮换使用，避免单个key使用频率过高
GEMINI_API_KEYS = [
    "your_first_api_key_here",
    "your_second_api_key_here",
    # 可以添加更多API key
]
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

# 表格压缩配置
BATCH_SIZE = 50         # 批处理大小
OVERLAP_SIZE = 5        # 重叠大小（相邻批次之间的重叠行数）
```

### 3A. 聊天转表格模式使用方法

#### 准备聊天数据
将您的聊天记录整理为JSON格式，放入 `data/chat.json`：
```json
[
    {"role": "user", "content": "用户消息内容"},
    {"role": "assistant", "content": "AI回复内容"},
    ...
]
```

#### 运行转换程序
```bash
python chat_to_table.py
```

### 3B. 表格压缩模式使用方法

#### 准备表格数据
将需要压缩的表格文件放入 `data/tables/` 目录，或者将表格数据整理为JSON格式放入 `data/table_data.json`：

#### 运行压缩程序
```bash
python table_compression.py
```

程序会：
1. 自动备份原始表格数据
2. 智能分批处理大型表格（默认每批50行，重叠5行）
3. 调用AI进行重复数据识别和内容整合
4. 生成压缩后的表格和JSON导出文件
5. 提供压缩统计和详细日志

### 4. 导入到SillyTavern酒馆
将生成的 `result/*/tables_formatted.json` 文件导入到 [SillyTavern酒馆记忆增强插件](https://github.com/muyoou/st-memory-enhancement) 中即可！

## ⚙️ 配置说明

### API配置
- `GEMINI_API_KEYS`: Google Gemini API密钥列表（支持多个密钥轮换使用）
- `GEMINI_MODEL`: 使用的模型版本
- `MAX_CONTEXT_LENGTH`: 最大上下文长度（默认49条）

### 表格压缩配置
- `BATCH_SIZE`: 分批处理时每批的行数（默认50行）
- `OVERLAP_SIZE`: 相邻批次间的重叠行数（默认5行）
- `TARGET_TABLE_INDEX`: 主要压缩目标表格的索引（默认4，即重要事件表，压缩其他表格请自行更改提示词）

### 路径配置
- `DATA_ROOT_DIR`: 数据根目录（默认"data"）
- `OUTPUT_ROOT_DIR`: 输出根目录（默认"result"）
- `CHAT_TO_TABLE_OUTPUT_DIR`: 聊天转表格输出目录
- `TABLE_COMPRESSION_OUTPUT_DIR`: 表格压缩输出目录

### 表格结构
所有表格结构遵循酒馆记忆增强插件规范，确保完美兼容。

---

## 🔗 相关链接

- **[SillyTavern 酒馆记忆增强插件](https://github.com/muyoou/st-memory-enhancement)** - 本工具的配套插件
- **[SillyTavern官方项目](https://github.com/SillyTavern/SillyTavern)** - AI角色扮演聊天平台



---

## ⚠️ 注意事项

### 通用注意事项
1. **导入须知**：在导入表格之前必须在当前聊天中有过至少一次对话，否则会报错"没有记录载体"或者无法读取记忆
1. **API配额管理**: 大型表格压缩会消耗较多API调用，建议配置多个API密钥
1. **版本适配**：建议使用酒馆记忆增强插件V2.0.3版本，后续可能不适配。

---

## 🤝 贡献与支持

欢迎提交Issue和Pull Request！如果本工具对您有帮助，请考虑：
- ⭐ 给项目点个Star
- 🔄 分享给更多酒馆用户
- 💬 在酒馆记忆增强插件社群中交流使用心得

**让我们一起让酒馆的记忆更加智能和高效！** ✨