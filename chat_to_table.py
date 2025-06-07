#!/usr/bin/env python3
"""
大语言模型表格化记忆系统 - 主程序
"""

import os
import json
import logging
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 导入配置和模块
from config import (
    LOG_LEVEL, LOG_FORMAT, GEMINI_API_KEYS,
)
from src.utils import (
    get_project_folder, get_input_chat_file,
    ensure_output_directories
)
from src.table_manager import TableManager
from src.chat_processor import ChatProcessor
from src.prompt_handler import PromptHandler
from src.llm_client import GeminiClient

# 设置日志
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


def setup_output_environment():
    """设置输出环境"""
    # 为聊天转表格设置输出目录
    project_folder = get_project_folder()
    output_path, tables_path = ensure_output_directories("chat_to_table")
    return output_path, project_folder


def save_llm_interaction(output_path: str, prompt: str, response: str, is_mock: bool = False):
    """保存LLM交互记录到JSON文件"""
    try:
        # 创建交互记录
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "is_mock_response": is_mock,
            "input_prompt": prompt if prompt is not None else "",
            "llm_response": response if response is not None else "",
            "prompt_length": len(prompt) if prompt is not None else 0,
            "response_length": len(response) if response is not None else 0
        }
        
        # 保存到输出目录的JSON文件
        interaction_file = os.path.join(output_path, "llm_interactions.json")
        
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
        logging.error(f"保存LLM交互记录失败: {e}")
        return None


def save_table_operations_analysis(output_path: str, round_index: int, llm_response: str,
                                   operations: list, execution_results: list) -> str:
    """保存表格操作解析结果到文件"""
    try:
        # 创建操作分析记录
        analysis_record = {
            "timestamp": datetime.now().isoformat(),
            "round_index": round_index + 1,  # 显示为1-based索引
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
        operations_file = os.path.join(output_path, "table_operations_analysis.json")
        
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
        logging.error(f"保存表格操作分析失败: {e}")
        return None


def main():
    """主程序入口"""
    console = Console()
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "🧠 大语言模型表格化记忆系统 - 聊天转表格模式",
        style="bold green"
    ))
    
    # 设置输出环境
    output_path, project_folder = setup_output_environment()
    console.print(f"📁 创建输出项目: {project_folder}")
    console.print(f"✅ 输出目录已准备: {output_path}")
    
    # 初始化系统组件
    try:
        # 使用输出目录的tables子目录
        tables_output_dir = os.path.join(output_path, "tables")
        table_manager = TableManager(tables_dir=tables_output_dir)
        chat_processor = ChatProcessor()
        prompt_handler = PromptHandler(table_manager)
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
                console.print(
                    f"[green]✅ Gemini API客户端已准备就绪（使用{len(GEMINI_API_KEYS)}个API key轮换模式）[/green]")
        
        console.print("✅ 组件初始化成功")
        
        # 检查是否存在输入聊天数据文件
        input_chat_file = get_input_chat_file()
        
        if os.path.exists(input_chat_file):
            console.print(f"[yellow]📖 正在加载聊天数据: {input_chat_file}[/yellow]")
            if not chat_processor.load_chat_data_from_file(input_chat_file):
                console.print("[red]❌ 加载聊天数据失败[/red]")
                return
            # 复制到输出目录
            import shutil
            output_chat_file = os.path.join(output_path, "chat.json")
            shutil.copy2(input_chat_file, output_chat_file)
            console.print(f"[blue]📋 已复制聊天数据到输出目录: {output_chat_file}[/blue]")
        else:
            console.print(f"[red]❌ 未找到聊天数据文件: {input_chat_file}[/red]")
            console.print(f"请确保文件存在并包含有效的聊天数据")
            return
        
        # 获取消息对列表
        message_pairs = chat_processor.get_message_pairs()
        if not message_pairs:
            console.print("[red]❌ 没有找到对话数据[/red]")
            return
        
        console.print(f"[blue]📝 共找到 {len(message_pairs)} 轮对话[/blue]")
        
        # 逐轮处理对话
        for pair_index, current_pair in enumerate(message_pairs):
            console.print(f"\n[bold blue]🔄 处理第 {pair_index + 1}/{len(message_pairs)} 轮对话[/bold blue]")
            
            # 获取历史对话内容
            history_content = chat_processor.get_conversation_history_up_to_pair(pair_index)
            
            # 获取当前轮对话内容
            current_content = chat_processor.get_current_pair_content(pair_index)
            
            # 合并历史和当前内容
            full_conversation = history_content + current_content
            
            console.print(f"[blue]📝 当前轮对话长度: {len(current_content)} 字符[/blue]")
            console.print(f"[blue]📝 历史对话长度: {len(history_content)} 字符[/blue]")
            
            # 获取当前轮的用户输入
            current_user_input = ""
            if current_pair and len(current_pair) >= 2:
                # current_pair是一个包含用户消息和助手消息的列表
                user_message = current_pair[0]  # 用户消息
                if isinstance(user_message, dict) and 'content' in user_message:
                    current_user_input = user_message['content']
                elif hasattr(user_message, 'content'):
                    current_user_input = user_message.content
            
            # 生成包含当前表格状态的提示词
            prompt = prompt_handler.generate_prompt_with_tables(full_conversation, current_user_input, pair_index)
            console.print(f"[cyan]💬 提示词总长度: {len(prompt)} 字符[/cyan]")
            
            # 执行LLM调用
            console.print(f"[blue]🤖 正在分析第 {pair_index + 1} 轮对话...[/blue]")
            
            # 直接使用真实API
            if GEMINI_API_KEYS and llm_client.is_available():
                console.print("[blue]📡 调用Gemini API...[/blue]")
                llm_response = llm_client.generate_content(prompt)
                is_mock_mode = False
            else:
                console.print("[red]❌ 无法访问Gemini API，请检查GEMINI_API_KEYS设置[/red]")
                return
            
            # 无论成功失败都保存交互记录
            interaction_file = save_llm_interaction(
                output_path,
                prompt,
                llm_response if llm_response else f"[第{pair_index + 1}轮] API调用失败 - 内容被过滤或其他错误",
                is_mock_mode
            )
            if interaction_file:
                console.print(f"[blue]💾 交互记录已保存: {interaction_file}[/blue]")
            
            if llm_response:
                console.print(f"[green]✅ 第 {pair_index + 1} 轮响应成功[/green]")
                console.print(f"[dim]响应内容:\n{llm_response}\n[/dim]")
                
                # 提取并执行表格操作
                operations = prompt_handler.extract_table_operations(llm_response)
                if operations:
                    console.print(f"[yellow]📋 第 {pair_index + 1} 轮解析到 {len(operations)} 个表格操作[/yellow]")
                    for i, op in enumerate(operations, 1):
                        console.print(f"  {i}. {op}")
                    
                    # 执行操作
                    results = prompt_handler.execute_operations(operations)
                    success_count = sum(results)
                    console.print(
                        f"[green]✅ 第 {pair_index + 1} 轮成功执行 {success_count}/{len(operations)} 个操作[/green]")
                    
                    # 显示更新后的表格状态
                    show_table_summary(table_manager, console)
                    
                    # 保存表格操作解析结果
                    operations_file = save_table_operations_analysis(
                        output_path,
                        pair_index,
                        llm_response,
                        operations,
                        results
                    )
                    if operations_file:
                        console.print(f"[blue]💾 表格操作分析已保存: {operations_file}[/blue]")
                
                else:
                    console.print(f"[yellow]⚠️ 第 {pair_index + 1} 轮未解析到表格操作[/yellow]")
                    
                    # 即使没有操作也保存分析记录
                    operations_file = save_table_operations_analysis(
                        output_path,
                        pair_index,
                        llm_response,
                        [],  # 空操作列表
                        []  # 空结果列表
                    )
                    if operations_file:
                        console.print(f"[blue]💾 表格操作分析已保存(无操作): {operations_file}[/blue]")
            else:
                console.print(f"[red]❌ 第 {pair_index + 1} 轮响应生成失败[/red]")
                console.print(f"[yellow]⚠️ 跳过第 {pair_index + 1} 轮，继续处理下一轮[/yellow]")
                continue  # 继续处理下一轮，而不是break
        
        console.print(f"\n[bold green]🎉 处理完成！共处理 {len(message_pairs)} 轮对话[/bold green]")
        console.print(f"[bold green]表格文件保存在: {output_path}/tables[/bold green]")
        
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
        console.print(f"[bold red]❌ 处理过程中出错: {e}[/bold red]")
        import traceback
        traceback.print_exc()


def show_table_summary(table_manager: TableManager, console: Console):
    """显示表格状态摘要"""
    console.print("\n[bold blue]📊 当前表格状态[/bold blue]")
    
    tables_info = table_manager.get_all_tables_info()
    
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("表格名称", style="cyan")
    summary_table.add_column("行数", justify="right", style="green")
    summary_table.add_column("文件路径", style="dim")
    
    for table_index, info in tables_info.items():
        summary_table.add_row(
            info['name'],
            str(info['row_count']),
            info['file_path']
        )
    
    console.print(summary_table)


if __name__ == "__main__":
    main()
