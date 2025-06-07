#!/usr/bin/env python3
"""
大语言模型表格化记忆系统 - 表格压缩主程序
"""

import os
import json
import logging
import shutil
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress

# 导入配置和模块
from config import (
    LOG_LEVEL, LOG_FORMAT, GEMINI_API_KEYS,
)
from src.utils import (
    get_project_folder, get_input_tables_dir,
    ensure_output_directories
)
from src.table_manager import TableManager
from src.prompt_handler import PromptHandler
from src.llm_client import GeminiClient
from src.table_schemas import TABLE_SCHEMAS

# 设置日志
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


def convert_json_to_tables(json_file_path: str, tables_dir: str, console: Console) -> bool:
    """
    将JSON格式的表格数据转换为CSV表格文件并覆盖现有文件

    Args:
        json_file_path: JSON文件路径
        tables_dir: 表格目录路径
        console: 控制台对象

    Returns:
        转换是否成功
    """
    try:
        console.print(f"[yellow]🔄 开始转换 {json_file_path} 到表格文件...[/yellow]")

        # 读取JSON文件，尝试不同的编码方式
        json_data = None
        for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'utf-16']:
            try:
                with open(json_file_path, 'r', encoding=encoding) as f:
                    json_data = json.load(f)
                console.print(f"[green]✅ 使用 {encoding} 编码成功读取JSON文件[/green]")
                break
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                console.print(f"[yellow]⚠️ 使用 {encoding} 编码读取失败: {str(e)[:100]}...[/yellow]")
                continue

        if json_data is None:
            raise Exception("无法使用任何编码方式读取JSON文件")

        # 确保输出目录存在
        os.makedirs(tables_dir, exist_ok=True)

        # 创建表格名到索引的映射（考虑<user>占位符）
        name_to_index = {}
        for index, schema in TABLE_SCHEMAS.items():
            name_to_index[schema['name']] = index
            # 同时处理包含"<user>"的表格名
            if "真银铃" in schema['name']:
                user_name = schema['name'].replace("真银铃", "<user>")
                name_to_index[user_name] = index

        converted_count = 0

        # 遍历JSON中的每个表格
        for sheet_id, sheet_data in json_data.items():
            if sheet_id == "mate":  # 跳过元数据
                continue

            table_name = sheet_data.get('name', '')
            content = sheet_data.get('content', [])

            if not content:
                console.print(f"[yellow]⚠️ 表格 {table_name} 内容为空，跳过[/yellow]")
                continue

            # 根据表格名找到对应的索引和文件名
            table_index = name_to_index.get(table_name)
            if table_index is None:
                console.print(f"[yellow]⚠️ 未找到表格 {table_name} 的映射，跳过[/yellow]")
                continue

            schema = TABLE_SCHEMAS[table_index]
            output_file = os.path.join(tables_dir, schema['file_name'])

            # 转换内容格式（移除第一列的None值）
            csv_data = []
            for row in content:
                if row and len(row) > 1:
                    # 移除第一列的None值，保留后面的数据
                    csv_row = row[1:]
                    csv_data.append(csv_row)

            if not csv_data:
                console.print(f"[yellow]⚠️ 表格 {table_name} 转换后数据为空，跳过[/yellow]")
                continue

            # 创建DataFrame并保存为CSV
            df = pd.DataFrame(csv_data[1:], columns=csv_data[0])  # 第一行作为列名
            df.to_csv(output_file, index=False, encoding='utf-8-sig')

            console.print(f"[green]✅ 已转换: {table_name} -> {output_file} ({len(df)} 行数据)[/green]")
            converted_count += 1

        console.print(f"[green]🎉 JSON转换完成！共转换 {converted_count} 个表格[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ JSON转换失败: {e}[/red]")
        logging.error(f"JSON转换错误: {e}")
        return False


def check_and_convert_json_data(data_dir: str, console: Console) -> bool:
    """
    检查data目录中是否有table_data.json文件，如果有则转换为表格文件

    Args:
        data_dir: data目录路径
        console: 控制台对象

    Returns:
        是否发现并转换了JSON文件
    """
    json_file_path = os.path.join(data_dir, "table_data.json")
    tables_dir = os.path.join(data_dir, "tables")

    if os.path.exists(json_file_path):
        console.print(f"[cyan]📋 发现 table_data.json 文件: {json_file_path}[/cyan]")

        # 直接转换JSON到tables目录（覆盖现有文件）
        success = convert_json_to_tables(json_file_path, tables_dir, console)

        if success:
            console.print(f"[green]✅ table_data.json 转换成功，表格文件已更新到 {tables_dir}[/green]")
            return True
        else:
            console.print(f"[red]❌ table_data.json 转换失败[/red]")
            return False
    else:
        console.print(f"[blue]ℹ️ 未发现 table_data.json 文件，使用现有表格[/blue]")
        return False


def setup_compression_environment():
    """设置表格压缩环境"""
    # 为表格压缩设置输出目录
    project_folder = get_project_folder()
    output_path, tables_path = ensure_output_directories("table_compression")
    return output_path, project_folder


def backup_input_tables(input_tables_dir: str, output_path: str) -> str:
    """
    备份输入表格到输出目录

    Args:
        input_tables_dir: 输入表格目录
        output_path: 输出目录路径

    Returns:
        备份目录路径
    """
    try:
        # 创建带时间戳的备份目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(output_path, f"backup_{timestamp}")

        # 复制整个输入表格目录
        if os.path.exists(input_tables_dir):
            shutil.copytree(input_tables_dir, backup_dir)
            return backup_dir
        else:
            raise FileNotFoundError(f"输入表格目录不存在: {input_tables_dir}")

    except Exception as e:
        logging.error(f"备份输入表格失败: {e}")
        raise


def copy_non_target_tables(input_tables_dir: str, output_tables_dir: str, target_table_index: int, console):
    """复制除目标表格外的其他所有表格到输出目录"""
    import shutil
    from src.table_schemas import TABLE_SCHEMAS

    console.print(f"[yellow]📋 正在复制其他表格文件...[/yellow]")

    for table_index, schema in TABLE_SCHEMAS.items():
        if table_index != target_table_index:  # 跳过要压缩的目标表格
            source_file = os.path.join(input_tables_dir, schema['file_name'])
            dest_file = os.path.join(output_tables_dir, schema['file_name'])

            if os.path.exists(source_file):
                try:
                    shutil.copy2(source_file, dest_file)
                    console.print(f"[green]✅ 已复制: {schema['name']} -> {dest_file}[/green]")
                except Exception as e:
                    console.print(f"[red]❌ 复制失败: {schema['name']} - {e}[/red]")
            else:
                console.print(f"[yellow]⚠️ 源文件不存在: {source_file}[/yellow]")

    console.print(f"[green]✅ 其他表格复制完成[/green]")


def create_batch_table_manager(input_tables_dir: str, output_tables_dir: str, table_index: int, start_row: int, batch_size: int, is_first_batch: bool = False):
    """
    创建用于分批处理的表格管理器

    Args:
        input_tables_dir: 输入表格目录
        output_tables_dir: 输出表格目录
        table_index: 要处理的表格索引
        start_row: 开始行号（从0开始）
        batch_size: 批处理大小
        is_first_batch: 是否是第一个批次

    Returns:
        处理过的TableManager实例
    """
    from src.table_schemas import TABLE_SCHEMAS
    import pandas as pd
    import tempfile
    import os

    # 读取输入表格数据
    schema = TABLE_SCHEMAS[table_index]
    input_file = os.path.join(input_tables_dir, schema['file_name'])

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"输入表格文件不存在: {input_file}")

    # 读取完整数据
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    # 提取批次数据
    end_row = min(start_row + batch_size, len(df))
    batch_df = df.iloc[start_row:end_row].copy()

    # 重置索引
    batch_df.reset_index(drop=True, inplace=True)

    # 创建临时目录给每个批次独立使用
    temp_dir = tempfile.mkdtemp(prefix=f"batch_{start_row}_")
    table_manager = TableManager(tables_dir=temp_dir)

    # 为这个批次创建一个空表格，让AI从头insert
    empty_df = pd.DataFrame(columns=batch_df.columns)
    table_manager.save_table(table_index, empty_df)

    return table_manager, len(df), batch_df, temp_dir





def merge_batch_results(input_tables_dir: str, output_tables_dir: str, table_index: int,
                       start_row: int, processed_df, console: Console, is_first_batch: bool = False) -> int:
    """
    将批次处理结果合并回主表格 - 简化版本：AI只insert，我们追加到总表

    Args:
        input_tables_dir: 输入表格目录
        output_tables_dir: 输出表格目录
        table_index: 表格索引
        start_row: 开始行号（用于显示，实际处理中不需要）
        processed_df: AI处理后的DataFrame（只包含新插入的数据）
        is_first_batch: 是否是第一个批次

    Returns:
        实际插入的行数
    """
    from src.table_schemas import TABLE_SCHEMAS
    import pandas as pd

    schema = TABLE_SCHEMAS[table_index]
    output_file = os.path.join(output_tables_dir, schema['file_name'])

    # 确保输出目录存在
    os.makedirs(output_tables_dir, exist_ok=True)

    # 如果输出文件不存在，创建空表格
    if not os.path.exists(output_file):
        # 创建空的DataFrame，使用原表的列结构
        input_file = os.path.join(input_tables_dir, schema['file_name'])
        sample_df = pd.read_csv(input_file, encoding='utf-8-sig', nrows=0)  # 只读取列名
        sample_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # 读取当前输出文件
    try:
        full_df = pd.read_csv(output_file, encoding='utf-8-sig')
    except Exception as e:
        console.print(f"[yellow]⚠️ 读取输出文件失败，创建新文件: {e}[/yellow]")
        # 如果读取失败，创建空DataFrame
        input_file = os.path.join(input_tables_dir, schema['file_name'])
        full_df = pd.read_csv(input_file, encoding='utf-8-sig', nrows=0)

    console.print(f"[blue]📊 合并前 - 主表格行数: {len(full_df)}, 新增数据行数: {len(processed_df)}[/blue]")

    # 将AI产生的新数据追加到总表后面
    if len(processed_df) > 0:
        # 确保列名一致性：processed_df的列名要和full_df一致
        if not full_df.empty:
            # 如果目标表格已有数据，确保新数据使用相同的列名
            if list(processed_df.columns) != list(full_df.columns):
                console.print(f"[yellow]⚠️ 检测到列名不一致，正在修复...[/yellow]")
                console.print(f"目标表格列名: {list(full_df.columns)}")
                console.print(f"新数据列名: {list(processed_df.columns)}")

                # 重新排列新数据的列，使其与目标表格一致
                processed_df_aligned = pd.DataFrame(columns=full_df.columns)
                for _, row in processed_df.iterrows():
                    processed_df_aligned = pd.concat([processed_df_aligned, pd.DataFrame([row.values], columns=full_df.columns)], ignore_index=True)
                processed_df = processed_df_aligned
        else:
            # 如果目标表格为空，确保至少有列名
            if full_df.empty and processed_df.empty:
                console.print(f"[yellow]⚠️ 主表格和新数据都为空[/yellow]")
                return 0

        # 追加新数据
        try:
            updated_df = pd.concat([full_df, processed_df], ignore_index=True)
            # 保存更新后的文件
            updated_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            console.print(f"[green]✅ 成功保存到 {output_file}, 共 {len(updated_df)} 行[/green]")
            return len(processed_df)
        except Exception as e:
            console.print(f"[red]❌ 保存文件失败: {e}[/red]")
            return 0

    console.print(f"[yellow]⚠️ 没有新数据需要合并[/yellow]")
    return 0


def save_compression_interaction(output_path: str, prompt: str, response: str, is_mock: bool = False):
    """保存表格压缩LLM交互记录到JSON文件"""
    try:
        # 创建交互记录
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": "table_compression",
            "is_mock_response": is_mock,
            "input_prompt": prompt if prompt is not None else "",
            "llm_response": response if response is not None else "",
            "prompt_length": len(prompt) if prompt is not None else 0,
            "response_length": len(response) if response is not None else 0
        }

        # 保存到输出目录的JSON文件
        interaction_file = os.path.join(output_path, "table_compression_interactions.json")

        # 如果文件已存在，加载现有记录
        existing_records = []
        if os.path.exists(interaction_file):
            try:
                with open(interaction_file, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            except:
                existing_records = []

        # 添加新记录
        existing_records.append(interaction_record)

        # 保存回文件
        with open(interaction_file, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, ensure_ascii=False, indent=2)

        return interaction_file

    except Exception as e:
        logging.error(f"保存表格压缩LLM交互记录失败: {e}")
        return None


def save_compression_operations_analysis(output_path: str, llm_response: str,
                                         operations: list, execution_results: list) -> str:
    """保存表格压缩操作解析结果到文件"""
    try:
        # 创建操作分析记录
        analysis_record = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": "table_compression",
            "llm_raw_output": llm_response,
            "parsed_operations": [],
            "execution_results": [],
            "summary": {
                "total_operations": len(operations),
                "successful_operations": sum(execution_results) if execution_results else 0,
                "failed_operations": len(execution_results) - sum(execution_results) if execution_results else 0
            }
        }

        # 解析操作详情
        for i, operation in enumerate(operations):
            operation_str = str(operation)
            operation_detail = {
                "index": i + 1,
                "operation": operation_str,
                "success": execution_results[i] if i < len(execution_results) else False,
                "operation_type": operation_str.split('(')[0] if '(' in operation_str else "unknown"
            }
            analysis_record["parsed_operations"].append(operation_detail)

        # 执行结果详情
        for i, result in enumerate(execution_results):
            operation_str = str(operations[i]) if i < len(operations) else "unknown"
            result_detail = {
                "operation_index": i + 1,
                "success": result,
                "operation": operation_str
            }
            analysis_record["execution_results"].append(result_detail)

        # 保存到输出目录的JSON文件
        operations_file = os.path.join(output_path, "table_compression_operations_analysis.json")

        # 如果文件已存在，加载现有记录
        existing_records = []
        if os.path.exists(operations_file):
            try:
                with open(operations_file, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            except:
                existing_records = []

        # 添加新记录
        existing_records.append(analysis_record)

        # 保存回文件
        with open(operations_file, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, ensure_ascii=False, indent=2)

        return operations_file

    except Exception as e:
        logging.error(f"保存表格压缩操作分析失败: {e}")
        return None


def main():
    """表格压缩主程序入口 - 分批处理模式"""
    console = Console()

    # 显示欢迎信息
    console.print(Panel.fit(
        "🗜️ 大语言模型表格化记忆系统 - 分批表格压缩模式",
        style="bold blue"
    ))

    try:
        # 设置压缩环境
        output_path, project_folder = setup_compression_environment()
        console.print(f"📁 创建压缩输出项目: {project_folder}")
        console.print(f"✅ 输出目录已准备: {output_path}")

        # 获取输入和输出目录
        input_tables_dir = get_input_tables_dir()
        output_tables_dir = os.path.join(output_path, "tables")

                # 检查并转换JSON数据（如果存在table_data.json）
        data_dir = os.path.dirname(input_tables_dir)  # data目录
        json_converted = check_and_convert_json_data(data_dir, console)

        if json_converted:
            console.print(f"[green]✅ 已从 table_data.json 更新表格文件[/green]")

        # 检查输入表格目录是否存在
        if not os.path.exists(input_tables_dir):
            console.print(f"[red]❌ 输入表格目录不存在: {input_tables_dir}[/red]")
            console.print(f"请确保在 {input_tables_dir} 目录下有要处理的表格文件")
            return

        # 备份输入表格
        console.print(f"[yellow]📋 正在备份输入表格...[/yellow]")
        backup_dir = backup_input_tables(input_tables_dir, output_path)
        console.print(f"[green]✅ 表格已备份到: {backup_dir}[/green]")



        # 初始化LLM客户端
        llm_client = GeminiClient()

        # 检查API配置状态
        if not GEMINI_API_KEYS:
            console.print("[yellow]⚠️ 未设置GEMINI_API_KEYS，使用模拟模式[/yellow]")
        elif not llm_client.is_available():
            console.print("[yellow]⚠️ Gemini客户端初始化失败，使用模拟模式[/yellow]")
        else:
            if len(GEMINI_API_KEYS) == 1:
                console.print("[green]✅ Gemini API客户端已准备就绪（使用单个API key）[/green]")
            else:
                console.print(f"[green]✅ Gemini API客户端已准备就绪（使用{len(GEMINI_API_KEYS)}个API key轮换模式）[/green]")

        # 配置分批处理参数
        TARGET_TABLE_INDEX = 4  # important_events_table.csv 的索引

        # 首先复制其他表格到输出目录（除了要压缩的表格4）
        copy_non_target_tables(input_tables_dir, output_tables_dir, TARGET_TABLE_INDEX, console)

        # 从配置文件导入批处理参数
        from config import BATCH_SIZE, OVERLAP_SIZE

        # 检查目标表格是否存在
        from src.table_schemas import TABLE_SCHEMAS
        target_schema = TABLE_SCHEMAS[TARGET_TABLE_INDEX]
        target_file = os.path.join(input_tables_dir, target_schema['file_name'])

        if not os.path.exists(target_file):
            console.print(f"[red]❌ 目标表格文件不存在: {target_file}[/red]")
            return

        # 读取目标表格，获取总行数
        import pandas as pd
        df = pd.read_csv(target_file, encoding='utf-8-sig')
        total_rows = len(df)

        console.print(f"[blue]📊 目标表格: {target_schema['name']}[/blue]")
        console.print(f"[blue]📊 总行数: {total_rows}[/blue]")
        console.print(f"[blue]📊 批处理大小: {BATCH_SIZE}[/blue]")
        console.print(f"[blue]📊 重叠大小: {OVERLAP_SIZE}[/blue]")

        # 计算总批次数
        step_size = BATCH_SIZE - OVERLAP_SIZE  # 每次前进的步长
        total_batches = ((total_rows - OVERLAP_SIZE - 1) // step_size) + 1

        console.print(f"[blue]📊 计划处理批次: {total_batches}[/blue]")
        console.print(f"[blue]📊 每批步长: {step_size}[/blue]")

        # 显示队列格式预览
        console.print(f"[blue]📊 队列格式预览:[/blue]")
        for preview_batch in range(min(3, total_batches)):
            preview_start = preview_batch * step_size
            preview_end = min(preview_start + BATCH_SIZE, total_rows)
            overlap_info = f"(重叠{OVERLAP_SIZE}行)" if preview_batch > 0 else "(首批)"
            console.print(f"[blue]  批次{preview_batch + 1}: 行 {preview_start + 1}-{preview_end} (共{preview_end - preview_start}行) {overlap_info}[/blue]")
        if total_batches > 3:
            console.print(f"[blue]  ... 还有 {total_batches - 3} 个批次[/blue]")

        # 开始分批处理
        with Progress() as progress:
            task = progress.add_task("[green]处理表格压缩...", total=total_batches)

            for batch_num in range(total_batches):
                start_row = batch_num * step_size
                end_row = min(start_row + BATCH_SIZE, total_rows)
                actual_batch_size = end_row - start_row

                progress.update(task, description=f"[green]处理批次 {batch_num + 1}/{total_batches} (行 {start_row + 1}-{end_row})")

                console.print(f"\n[bold blue]🔄 处理批次 {batch_num + 1}/{total_batches}[/bold blue]")
                console.print(f"[cyan]📝 处理行范围: {start_row + 1} 到 {end_row} (共 {actual_batch_size} 行)[/cyan]")

                try:
                    # 创建批次表格管理器
                    batch_table_manager, _, batch_df, temp_dir = create_batch_table_manager(
                        input_tables_dir, output_tables_dir, TARGET_TABLE_INDEX, start_row, BATCH_SIZE,
                        is_first_batch=(batch_num == 0)
                    )

                    # 创建提示词处理器
                    prompt_handler = PromptHandler(batch_table_manager)

                    # 使用和chat_to_table.py相同的提示词生成逻辑，但使用MEMORY_TABLE_PROMPT_INTEGRATION
                    # 传入input_tables_dir以获取其他表格的完整数据
                    compression_prompt = prompt_handler.generate_prompt_with_tables("", "", 0, use_integration_prompt=True, input_tables_dir=input_tables_dir, batch_df=batch_df)
                    console.print(f"[cyan]💬 批次 {batch_num + 1}/{total_batches} 提示词长度: {len(compression_prompt)} 字符[/cyan]")

                    # 调用LLM进行表格压缩
                    console.print(f"[yellow]🤖 正在调用LLM处理批次 {batch_num + 1}...[/yellow]")

                    if llm_client.is_available():
                        # 使用真实API
                        llm_response = llm_client.generate_content(compression_prompt)
                        is_mock = False
                        console.print(f"[green]✅ 批次 {batch_num + 1} 获得LLM响应[/green]")
                    else:
                        # 使用模拟响应（可以保持原有的模拟响应方法）
                        llm_response = prompt_handler.simulate_compression_response()
                        is_mock = True
                        console.print(f"[yellow]✅ 批次 {batch_num + 1} 获得模拟LLM响应[/yellow]")

                    # 保存LLM交互记录
                    interaction_file = save_compression_interaction(
                        output_path,
                        f"批次{batch_num + 1}:\n{compression_prompt}",
                        llm_response,
                        is_mock
                    )

                    if llm_response:
                        # 提取并执行表格操作（与chat_to_table.py保持一致）
                        operations = prompt_handler.extract_table_operations(llm_response)

                        if operations:
                            console.print(f"[yellow]📋 批次 {batch_num + 1} 解析到 {len(operations)} 个表格操作[/yellow]")
                            for i, op in enumerate(operations, 1):
                                console.print(f"  {i}. {op}")

                            # 执行操作（与chat_to_table.py保持一致）
                            execution_results = prompt_handler.execute_operations(operations)
                            success_count = sum(execution_results)
                            console.print(f"[green]✅ 批次 {batch_num + 1} 成功执行 {success_count}/{len(operations)} 个操作[/green]")

                            # 获取处理后的数据并合并回主表格
                            processed_df = batch_table_manager.load_table(TARGET_TABLE_INDEX)
                            console.print(f"[blue]📊 批次 {batch_num + 1} 处理后的数据行数: {len(processed_df)}[/blue]")
                            if len(processed_df) > 0:
                                console.print(f"[blue]📊 批次 {batch_num + 1} 处理后数据预览:[/blue]")
                                for idx, row in processed_df.head(3).iterrows():
                                    console.print(f"  行{idx}: {dict(row)}")

                            actual_processed = merge_batch_results(
                                input_tables_dir, output_tables_dir, TARGET_TABLE_INDEX, start_row, processed_df, console,
                                is_first_batch=(batch_num == 0)
                            )

                            console.print(f"[green]✅ 批次 {batch_num + 1} 已合并 {actual_processed} 行到主表格[/green]")

                            # 保存操作分析结果
                            operations_file = save_compression_operations_analysis(
                                output_path, f"批次{batch_num + 1}:\n{llm_response}", operations, execution_results
                            )

                        else:
                            console.print(f"[yellow]⚠️ 批次 {batch_num + 1} 未解析到表格操作[/yellow]")

                            # 即使没有操作也保存分析记录（与chat_to_table.py保持一致）
                            operations_file = save_compression_operations_analysis(
                                output_path, f"批次{batch_num + 1}:\n{llm_response}", [], []
                            )

                    else:
                        console.print(f"[red]❌ 批次 {batch_num + 1} LLM响应生成失败[/red]")

                except Exception as e:
                    console.print(f"[red]❌ 批次 {batch_num + 1} 处理失败: {e}[/red]")
                    logging.error(f"批次 {batch_num + 1} 处理错误: {e}")
                finally:
                    # 清理临时目录
                    if 'temp_dir' in locals() and os.path.exists(temp_dir):
                        import shutil
                        try:
                            shutil.rmtree(temp_dir)
                        except:
                            pass

                progress.advance(task)

        # 显示最终结果
        console.print(f"\n[bold green]🎉 分批表格压缩完成！[/bold green]")
        console.print(f"[bold green]共处理 {total_batches} 个批次[/bold green]")
        console.print(f"[bold green]压缩结果保存在: {output_path}[/bold green]")
        console.print(f"[bold green]备份文件保存在: {backup_dir}[/bold green]")

        # 显示压缩后的表格统计
        if os.path.exists(os.path.join(output_tables_dir, target_schema['file_name'])):
            final_df = pd.read_csv(os.path.join(output_tables_dir, target_schema['file_name']), encoding='utf-8-sig')
            final_rows = len(final_df)
            compression_ratio = (total_rows - final_rows) / total_rows * 100 if total_rows > 0 else 0

            console.print(f"\n[bold blue]📊 压缩统计：[/bold blue]")
            console.print(f"[cyan]原始行数: {total_rows}[/cyan]")
            console.print(f"[cyan]压缩后行数: {final_rows}[/cyan]")
            console.print(f"[cyan]压缩比例: {compression_ratio:.2f}%[/cyan]")
            
            # 执行表格处理，转换为JSON格式
            console.print(f"\n[bold blue]📊 开始处理表格数据转换...[/bold blue]")
            try:
                from src.process_tables import process_tables_in_directory
                
                # 生成JSON格式的表格文件，保存到当前输出文件夹下
                tables_dir = os.path.join(output_path, "tables")
                json_output_file = os.path.join(output_path, "tables_formatted.json")
                
                if os.path.exists(tables_dir):
                    console.print(f"[cyan]📂 处理表格目录: {tables_dir}[/cyan]")
                    json_data = process_tables_in_directory(tables_dir, json_output_file)
                    console.print(f"[green]✅ 表格JSON格式已生成: {json_output_file}[/green]")
                    console.print(f"[cyan]📝 共转换 {len(json_data) - 1} 个表格（不包括mate信息）[/cyan]")
                    
                    # 显示转换的表格列表
                    console.print("\n[bold blue]📋 包含的表格：[/bold blue]")
                    for sheet_id, sheet_data in json_data.items():
                        if sheet_id != "mate":
                            name = sheet_data.get('name', 'Unknown')
                            rows = len(sheet_data.get('content', [])) - 1  # 减去表头行
                            console.print(f"  • [cyan]{name}[/cyan]: {rows} 行数据")
                else:
                    console.print(f"[yellow]⚠️ 表格目录不存在: {tables_dir}[/yellow]")
            
            except Exception as e:
                console.print(f"[red]❌ 表格处理过程中出错: {e}[/red]")
                import traceback
                traceback.print_exc()

    except Exception as e:
        console.print(f"[red]❌ 表格压缩过程中发生错误: {e}[/red]")
        logging.error(f"表格压缩错误: {e}")
        import traceback
        traceback.print_exc()


def show_table_summary(tables_dir: str, console: Console):
    """显示表格概要信息"""
    try:
        from src.table_schemas import TABLE_SCHEMAS
        import pandas as pd

        summary_table = Table(title="📊 表格数据概要")
        summary_table.add_column("表格", style="cyan")
        summary_table.add_column("行数", style="green")
        summary_table.add_column("状态", style="yellow")

        for i, schema in TABLE_SCHEMAS.items():
            try:
                table_file = os.path.join(tables_dir, schema['file_name'])
                if os.path.exists(table_file):
                    df = pd.read_csv(table_file, encoding='utf-8-sig')
                    row_count = len(df)
                    status = "有数据" if row_count > 0 else "空表格"
                else:
                    row_count = 0
                    status = "文件不存在"

                summary_table.add_row(f"{i}: {schema['name']}", str(row_count), status)
            except Exception as e:
                summary_table.add_row(f"{i}: {schema['name']}", "错误", str(e))

        console.print(summary_table)
        console.print()

    except Exception as e:
        console.print(f"[red]❌ 无法显示表格概要: {e}[/red]")


if __name__ == "__main__":
    main()
