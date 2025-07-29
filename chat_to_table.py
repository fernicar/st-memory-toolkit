#!/usr/bin/env python3
"""
Large Language Model Tabular Memory System - Main Program
"""

import os
import json
import logging
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import configurations and modules
from config import (
    LOG_LEVEL, LOG_FORMAT, GEMINI_API_KEYS,
)
from src.utils import (
    get_project_folder, get_input_chat_file,
    ensure_output_directories
)
from src.table_manager import TableManager
from src.conversation_processor import ConversationProcessor
from src.prompt_manager import PromptManager
from src.llm_client import GeminiClient

# Set up logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


def setup_output_environment():
    """Set up the output environment"""
    # Set up the output directory for chat_to_table
    project_folder = get_project_folder()
    output_path, tables_path = ensure_output_directories("chat_to_table")
    return output_path, project_folder


def save_llm_interaction(output_path: str, prompt: str, response: str, is_mock: bool = False):
    """Save LLM interaction records to a JSON file"""
    try:
        # Create an interaction record
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "is_mock_response": is_mock,
            "input_prompt": prompt if prompt is not None else "",
            "llm_response": response if response is not None else "",
            "prompt_length": len(prompt) if prompt is not None else 0,
            "response_length": len(response) if response is not None else 0
        }
        
        # Save to a JSON file in the output directory
        interaction_file = os.path.join(output_path, "llm_interactions.json")
        
        # If the file exists, load existing records
        existing_records = []
        if os.path.exists(interaction_file):
            try:
                with open(interaction_file, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            except:
                existing_records = []
        
        # Add the new record
        existing_records.append(interaction_record)
        
        # Save back to the file
        with open(interaction_file, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, ensure_ascii=False, indent=2)
        
        return interaction_file
    
    except Exception as e:
        logging.error(f"Failed to save LLM interaction record: {e}")
        return None


def save_table_operations_analysis(output_path: str, round_index: int, llm_response: str,
                                   operations: list, execution_results: list) -> str:
    """Save table operation analysis results to a file"""
    try:
        # Create an operation analysis record
        analysis_record = {
            "timestamp": datetime.now().isoformat(),
            "round_index": round_index + 1,  # Display as 1-based index
            "llm_raw_output": llm_response,
            "parsed_operations": [],
            "execution_results": [],
            "summary": {
                "total_operations": len(operations),
                "successful_operations": sum(execution_results) if execution_results else 0,
                "failed_operations": len(execution_results) - sum(execution_results) if execution_results else 0
            }
        }
        
        # Parse operation details
        for i, operation in enumerate(operations):
            operation_str = str(operation)
            operation_detail = {
                "index": i + 1,
                "operation": operation_str,
                "success": execution_results[i] if i < len(execution_results) else False,
                "operation_type": operation_str.split('(')[0] if '(' in operation_str else "unknown"
            }
            analysis_record["parsed_operations"].append(operation_detail)
        
        # Execution result details
        for i, result in enumerate(execution_results):
            operation_str = str(operations[i]) if i < len(operations) else "unknown"
            result_detail = {
                "operation_index": i + 1,
                "success": result,
                "operation": operation_str
            }
            analysis_record["execution_results"].append(result_detail)
        
        # Save to a JSON file in the output directory
        operations_file = os.path.join(output_path, "table_operations_analysis.json")
        
        # If the file exists, load existing records
        existing_records = []
        if os.path.exists(operations_file):
            try:
                with open(operations_file, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            except:
                existing_records = []
        
        # Add the new record
        existing_records.append(analysis_record)
        
        # Save back to the file
        with open(operations_file, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, ensure_ascii=False, indent=2)
        
        return operations_file
    
    except Exception as e:
        logging.error(f"Failed to save table operation analysis: {e}")
        return None


def main():
    """Main program entry point"""
    console = Console()
    
    # Display welcome message
    console.print(Panel.fit(
        "🧠 Large Language Model Tabular Memory System - Chat to Table Mode",
        style="bold green"
    ))
    
    # Set up the output environment
    output_path, project_folder = setup_output_environment()
    console.print(f"📁 Created output project: {project_folder}")
    console.print(f"✅ Output directory is ready: {output_path}")
    
    # Initialize system components
    try:
        # Use the tables subdirectory of the output directory
        tables_output_dir = os.path.join(output_path, "tables")
        table_manager = TableManager(tables_dir=tables_output_dir)
        chat_processor = ConversationProcessor()
        prompt_handler = PromptManager(table_manager)
        llm_client = GeminiClient()
        
        # Check API configuration status
        if not GEMINI_API_KEYS:
            console.print("[yellow]⚠️ GEMINI_API_KEYS not set, using mock mode[/yellow]")
        elif not llm_client.is_available():
            console.print("[yellow]⚠️ Gemini client initialization failed, using mock mode[/yellow]")
        else:
            if len(GEMINI_API_KEYS) == 1:
                console.print("[green]✅ Gemini API client is ready (using a single API key)[/green]")
            else:
                console.print(
                    f"[green]✅ Gemini API client is ready (using {len(GEMINI_API_KEYS)} API keys in rotation mode)[/green]")
        
        console.print("✅ Components initialized successfully")
        
        # Check if the input chat data file exists
        input_chat_file = get_input_chat_file()
        
        if os.path.exists(input_chat_file):
            console.print(f"[yellow]📖 Loading chat data: {input_chat_file}[/yellow]")
            if not chat_processor.load_chat_data_from_file(input_chat_file):
                console.print("[red]❌ Failed to load chat data[/red]")
                return
            # Copy to the output directory
            import shutil
            output_chat_file = os.path.join(output_path, "chat.json")
            shutil.copy2(input_chat_file, output_chat_file)
            console.print(f"[blue]📋 Copied chat data to the output directory: {output_chat_file}[/blue]")
        else:
            console.print(f"[red]❌ Chat data file not found: {input_chat_file}[/red]")
            console.print(f"Please make sure the file exists and contains valid chat data")
            return
        
        # Get the list of message pairs
        message_pairs = chat_processor.get_message_pairs()
        if not message_pairs:
            console.print("[red]❌ No conversation data found[/red]")
            return
        
        console.print(f"[blue]📝 Found {len(message_pairs)} conversation rounds[/blue]")
        
        # Process conversations round by round
        for pair_index, current_pair in enumerate(message_pairs):
            console.print(f"\n[bold blue]🔄 Processing round {pair_index + 1}/{len(message_pairs)}[/bold blue]")
            
            # Get historical conversation content
            history_content = chat_processor.get_conversation_history_up_to_pair(pair_index)
            
            # Get current round conversation content
            current_content = chat_processor.get_current_pair_content(pair_index)
            
            # Merge historical and current content
            full_conversation = history_content + current_content
            
            console.print(f"[blue]📝 Current round conversation length: {len(current_content)} characters[/blue]")
            console.print(f"[blue]📝 Historical conversation length: {len(history_content)} characters[/blue]")
            
            # Get the user input for the current round
            current_user_input = ""
            if current_pair and len(current_pair) >= 2:
                # current_pair is a list containing user and assistant messages
                user_message = current_pair[0]  # User message
                if isinstance(user_message, dict) and 'content' in user_message:
                    current_user_input = user_message['content']
                elif hasattr(user_message, 'content'):
                    current_user_input = user_message.content
            
            # Generate a prompt with the current table status
            prompt = prompt_handler.generate_prompt_with_tables(full_conversation, current_user_input, pair_index)
            console.print(f"[cyan]💬 Total prompt length: {len(prompt)} characters[/cyan]")
            
            # Execute LLM call
            console.print(f"[blue]🤖 Analyzing round {pair_index + 1}...[/blue]")
            
            # Use the real API directly
            if GEMINI_API_KEYS and llm_client.is_available():
                console.print("[blue]📡 Calling Gemini API...[/blue]")
                llm_response = llm_client.generate_content(prompt)
                is_mock_mode = False
            else:
                console.print("[red]❌ Cannot access Gemini API, please check GEMINI_API_KEYS settings[/red]")
                return
            
            # Save interaction record regardless of success or failure
            interaction_file = save_llm_interaction(
                output_path,
                prompt,
                llm_response if llm_response else f"[Round {pair_index + 1}] API call failed - content filtered or other error",
                is_mock_mode
            )
            if interaction_file:
                console.print(f"[blue]💾 Interaction record saved: {interaction_file}[/blue]")
            
            if llm_response:
                console.print(f"[green]✅ Round {pair_index + 1} response successful[/green]")
                console.print(f"[dim]Response content:\n{llm_response}\n[/dim]")
                
                # Extract and execute table operations
                operations = prompt_handler.extract_table_operations(llm_response)
                if operations:
                    console.print(f"[yellow]📋 Parsed {len(operations)} table operations in round {pair_index + 1}[/yellow]")
                    for i, op in enumerate(operations, 1):
                        console.print(f"  {i}. {op}")
                    
                    # Execute operations
                    results = prompt_handler.execute_operations(operations)
                    success_count = sum(results)
                    console.print(
                        f"[green]✅ Successfully executed {success_count}/{len(operations)} operations in round {pair_index + 1}[/green]")
                    
                    # Display updated table status
                    show_table_summary(table_manager, console)
                    
                    # Save table operation analysis results
                    operations_file = save_table_operations_analysis(
                        output_path,
                        pair_index,
                        llm_response,
                        operations,
                        results
                    )
                    if operations_file:
                        console.print(f"[blue]💾 Table operation analysis saved: {operations_file}[/blue]")
                
                else:
                    console.print(f"[yellow]⚠️ No table operations parsed in round {pair_index + 1}[/yellow]")
                    
                    # Save analysis record even if there are no operations
                    operations_file = save_table_operations_analysis(
                        output_path,
                        pair_index,
                        llm_response,
                        [],  # Empty operation list
                        []  # Empty result list
                    )
                    if operations_file:
                        console.print(f"[blue]💾 Table operation analysis saved (no operations): {operations_file}[/blue]")
            else:
                console.print(f"[red]❌ Round {pair_index + 1} response generation failed[/red]")
                console.print(f"[yellow]⚠️ Skipping round {pair_index + 1}, continuing to the next round[/yellow]")
                continue  # Continue to the next round instead of breaking
        
        console.print(f"\n[bold green]🎉 Processing complete! Processed {len(message_pairs)} conversation rounds[/bold green]")
        console.print(f"[bold green]Table files saved in: {output_path}/tables[/bold green]")
        
        # Execute table processing, convert to JSON format
        console.print(f"\n[bold blue]📊 Starting table data conversion...[/bold blue]")
        try:
            from src.table_converter import process_tables_in_directory
            
            # Generate JSON formatted table file and save it to the current output folder
            tables_dir = os.path.join(output_path, "tables")
            json_output_file = os.path.join(output_path, "tables_formatted.json")
            
            if os.path.exists(tables_dir):
                console.print(f"[cyan]📂 Processing table directory: {tables_dir}[/cyan]")
                json_data = process_tables_in_directory(tables_dir, json_output_file)
                console.print(f"[green]✅ Table JSON format generated: {json_output_file}[/green]")
                console.print(f"[cyan]📝 Converted {len(json_data) - 1} tables (excluding mate info)[/cyan]")
                
                # Display the list of converted tables
                console.print("\n[bold blue]📋 Included tables:[/bold blue]")
                for sheet_id, sheet_data in json_data.items():
                    if sheet_id != "mate":
                        name = sheet_data.get('name', 'Unknown')
                        rows = len(sheet_data.get('content', [])) - 1  # Subtract header row
                        console.print(f"  • [cyan]{name}[/cyan]: {rows} rows of data")
            else:
                console.print(f"[yellow]⚠️ Table directory not found: {tables_dir}[/yellow]")
        
        except Exception as e:
            console.print(f"[red]❌ Error during table processing: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        console.print(f"[bold red]❌ Error during processing: {e}[/bold red]")
        import traceback
        traceback.print_exc()


def show_table_summary(table_manager: TableManager, console: Console):
    """Display table status summary"""
    console.print("\n[bold blue]📊 Current table status[/bold blue]")
    
    tables_info = table_manager.get_all_tables_info()
    
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Table Name", style="cyan")
    summary_table.add_column("Row Count", justify="right", style="green")
    summary_table.add_column("File Path", style="dim")
    
    for table_index, info in tables_info.items():
        summary_table.add_row(
            info['name'],
            str(info['row_count']),
            info['file_path']
        )
    
    console.print(summary_table)


if __name__ == "__main__":
    main()
