#!/usr/bin/env python3
"""
Large Language Model Tabular Memory System - Table Compression Main Program
"""

import os
import json
import logging
import shutil
import pandas as pd
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress

# Import configurations and modules
from config import (
    LOG_LEVEL, LOG_FORMAT, GEMINI_API_KEYS,
)
from src.utils import (
    get_project_folder, get_input_tables_dir,
    ensure_output_directories
)
from src.table_manager import TableManager
from src.prompt_manager import PromptManager
from src.llm_client import GeminiClient
from src.table_schemas import TABLE_SCHEMAS

# Set up logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


def convert_json_to_tables(json_file_path: str, tables_dir: str, console: Console) -> bool:
    """
    Convert JSON formatted table data to CSV table files and overwrite existing files.

    Args:
        json_file_path: Path to the JSON file.
        tables_dir: Path to the tables directory.
        console: The console object.

    Returns:
        Whether the conversion was successful.
    """
    try:
        console.print(f"[yellow]🔄 Starting conversion of {json_file_path} to table files...[/yellow]")

        # Read the JSON file, trying different encodings
        json_data = None
        for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'utf-16']:
            try:
                with open(json_file_path, 'r', encoding=encoding) as f:
                    json_data = json.load(f)
                console.print(f"[green]✅ Successfully read JSON file with {encoding} encoding[/green]")
                break
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                console.print(f"[yellow]⚠️ Failed to read with {encoding} encoding: {str(e)[:100]}...[/yellow]")
                continue

        if json_data is None:
            raise Exception("Could not read JSON file with any encoding")

        # Ensure the output directory exists
        os.makedirs(tables_dir, exist_ok=True)

        # Create a mapping from table name to index (considering the <user> placeholder)
        name_to_index = {}
        for index, schema in TABLE_SCHEMAS.items():
            name_to_index[schema['name']] = index
            # Also handle table names containing "<user>"
            if "真银铃" in schema['name']:
                user_name = schema['name'].replace("真银铃", "<user>")
                name_to_index[user_name] = index

        converted_count = 0

        # Iterate over each table in the JSON
        for sheet_id, sheet_data in json_data.items():
            if sheet_id == "mate":  # Skip metadata
                continue

            table_name = sheet_data.get('name', '')
            content = sheet_data.get('content', [])

            if not content:
                console.print(f"[yellow]⚠️ Table {table_name} is empty, skipping[/yellow]")
                continue

            # Find the corresponding index and filename from the table name
            table_index = name_to_index.get(table_name)
            if table_index is None:
                console.print(f"[yellow]⚠️ No mapping found for table {table_name}, skipping[/yellow]")
                continue

            schema = TABLE_SCHEMAS[table_index]
            output_file = os.path.join(tables_dir, schema['file_name'])

            # Convert the content format (remove the None value in the first column)
            csv_data = []
            for row in content:
                if row and len(row) > 1:
                    # Remove the None value in the first column, keep the rest of the data
                    csv_row = row[1:]
                    csv_data.append(csv_row)

            if not csv_data:
                console.print(f"[yellow]⚠️ Data for table {table_name} is empty after conversion, skipping[/yellow]")
                continue

            # Create a DataFrame and save as CSV
            df = pd.DataFrame(csv_data[1:], columns=csv_data[0])  # First row as header
            df.to_csv(output_file, index=False, encoding='utf-8-sig')

            console.print(f"[green]✅ Converted: {table_name} -> {output_file} ({len(df)} rows)[/green]")
            converted_count += 1

        console.print(f"[green]🎉 JSON conversion complete! Converted {converted_count} tables[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ JSON conversion failed: {e}[/red]")
        logging.error(f"JSON conversion error: {e}")
        return False


def check_and_convert_json_data(data_dir: str, console: Console) -> bool:
    """
    Check for a table_data.json file in the data directory and convert it to table files if it exists.

    Args:
        data_dir: Path to the data directory.
        console: The console object.

    Returns:
        Whether a JSON file was found and converted.
    """
    json_file_path = os.path.join(data_dir, "table_data.json")
    tables_dir = os.path.join(data_dir, "tables")

    if os.path.exists(json_file_path):
        console.print(f"[cyan]📋 Found table_data.json file: {json_file_path}[/cyan]")

        # Directly convert JSON to the tables directory (overwriting existing files)
        success = convert_json_to_tables(json_file_path, tables_dir, console)

        if success:
            console.print(f"[green]✅ table_data.json converted successfully, table files updated in {tables_dir}[/green]")
            return True
        else:
            console.print(f"[red]❌ table_data.json conversion failed[/red]")
            return False
    else:
        console.print(f"[blue]ℹ️ table_data.json file not found, using existing tables[/blue]")
        return False


def setup_compression_environment():
    """Set up the table compression environment."""
    # Set up the output directory for table compression
    project_folder = get_project_folder()
    output_path, tables_path = ensure_output_directories("table_compression")
    return output_path, project_folder


def backup_input_tables(input_tables_dir: str, output_path: str) -> str:
    """
    Back up input tables to the output directory.

    Args:
        input_tables_dir: The input tables directory.
        output_path: The output directory path.

    Returns:
        The path to the backup directory.
    """
    try:
        # Create a timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(output_path, f"backup_{timestamp}")

        # Copy the entire input tables directory
        if os.path.exists(input_tables_dir):
            shutil.copytree(input_tables_dir, backup_dir)
            return backup_dir
        else:
            raise FileNotFoundError(f"Input tables directory not found: {input_tables_dir}")

    except Exception as e:
        logging.error(f"Failed to back up input tables: {e}")
        raise


def copy_non_target_tables(input_tables_dir: str, output_tables_dir: str, target_table_index: int, console):
    """Copy all tables except the target table to the output directory."""
    import shutil
    from src.table_schemas import TABLE_SCHEMAS

    console.print(f"[yellow]📋 Copying other table files...[/yellow]")

    for table_index, schema in TABLE_SCHEMAS.items():
        if table_index != target_table_index:  # Skip the target table to be compressed
            source_file = os.path.join(input_tables_dir, schema['file_name'])
            dest_file = os.path.join(output_tables_dir, schema['file_name'])

            if os.path.exists(source_file):
                try:
                    shutil.copy2(source_file, dest_file)
                    console.print(f"[green]✅ Copied: {schema['name']} -> {dest_file}[/green]")
                except Exception as e:
                    console.print(f"[red]❌ Failed to copy: {schema['name']} - {e}[/red]")
            else:
                console.print(f"[yellow]⚠️ Source file not found: {source_file}[/yellow]")

    console.print(f"[green]✅ Other tables copied successfully[/green]")


def create_batch_table_manager(input_tables_dir: str, output_tables_dir: str, table_index: int, start_row: int, batch_size: int, is_first_batch: bool = False):
    """
    Create a table manager for batch processing.

    Args:
        input_tables_dir: The input tables directory.
        output_tables_dir: The output tables directory.
        table_index: The index of the table to process.
        start_row: The starting row number (from 0).
        batch_size: The batch size.
        is_first_batch: Whether this is the first batch.

    Returns:
        A processed TableManager instance.
    """
    from src.table_schemas import TABLE_SCHEMAS
    import pandas as pd
    import tempfile
    import os

    # Read the input table data
    schema = TABLE_SCHEMAS[table_index]
    input_file = os.path.join(input_tables_dir, schema['file_name'])

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input table file not found: {input_file}")

    # Read the full data
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    # Extract the batch data
    end_row = min(start_row + batch_size, len(df))
    batch_df = df.iloc[start_row:end_row].copy()

    # Reset the index
    batch_df.reset_index(drop=True, inplace=True)

    # Create a temporary directory for each batch to use independently
    temp_dir = tempfile.mkdtemp(prefix=f"batch_{start_row}_")
    table_manager = TableManager(tables_dir=temp_dir)

    # Create an empty table for this batch, letting the AI insert from scratch
    empty_df = pd.DataFrame(columns=batch_df.columns)
    table_manager.save_table(table_index, empty_df)

    return table_manager, len(df), batch_df, temp_dir


def merge_batch_results(input_tables_dir: str, output_tables_dir: str, table_index: int,
                       start_row: int, processed_df, console: Console, is_first_batch: bool = False) -> int:
    """
    Merge the batch processing results back into the main table - simplified version: AI only inserts, we append to the main table.

    Args:
        input_tables_dir: The input tables directory.
        output_tables_dir: The output tables directory.
        table_index: The table index.
        start_row: The starting row number (for display, not actually used in processing).
        processed_df: The AI-processed DataFrame (contains only newly inserted data).
        is_first_batch: Whether this is the first batch.

    Returns:
        The number of rows actually inserted.
    """
    from src.table_schemas import TABLE_SCHEMAS
    import pandas as pd

    schema = TABLE_SCHEMAS[table_index]
    output_file = os.path.join(output_tables_dir, schema['file_name'])

    # Ensure the output directory exists
    os.makedirs(output_tables_dir, exist_ok=True)

    # If the output file does not exist, create an empty table
    if not os.path.exists(output_file):
        # Create an empty DataFrame with the column structure of the original table
        input_file = os.path.join(input_tables_dir, schema['file_name'])
        sample_df = pd.read_csv(input_file, encoding='utf-8-sig', nrows=0)  # Read only the header
        sample_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # Read the current output file
    try:
        full_df = pd.read_csv(output_file, encoding='utf-8-sig')
    except Exception as e:
        console.print(f"[yellow]⚠️ Failed to read output file, creating a new file: {e}[/yellow]")
        # If reading fails, create an empty DataFrame
        input_file = os.path.join(input_tables_dir, schema['file_name'])
        full_df = pd.read_csv(input_file, encoding='utf-8-sig', nrows=0)

    console.print(f"[blue]📊 Before merging - Main table rows: {len(full_df)}, New data rows: {len(processed_df)}[/blue]")

    # Append the new data generated by the AI to the main table
    if len(processed_df) > 0:
        # Ensure column name consistency: processed_df's columns should match full_df's
        if not full_df.empty:
            # If the target table already has data, ensure the new data uses the same columns
            if list(processed_df.columns) != list(full_df.columns):
                console.print(f"[yellow]⚠️ Detected column name mismatch, fixing...[/yellow]")
                console.print(f"Target table columns: {list(full_df.columns)}")
                console.print(f"New data columns: {list(processed_df.columns)}")

                # Reorder the columns of the new data to match the target table
                processed_df_aligned = pd.DataFrame(columns=full_df.columns)
                for _, row in processed_df.iterrows():
                    processed_df_aligned = pd.concat([processed_df_aligned, pd.DataFrame([row.values], columns=full_df.columns)], ignore_index=True)
                processed_df = processed_df_aligned
        else:
            # If the target table is empty, ensure it at least has columns
            if full_df.empty and processed_df.empty:
                console.print(f"[yellow]⚠️ Main table and new data are both empty[/yellow]")
                return 0

        # Append the new data
        try:
            updated_df = pd.concat([full_df, processed_df], ignore_index=True)
            # Save the updated file
            updated_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            console.print(f"[green]✅ Successfully saved to {output_file}, total {len(updated_df)} rows[/green]")
            return len(processed_df)
        except Exception as e:
            console.print(f"[red]❌ Failed to save file: {e}[/red]")
            return 0

    console.print(f"[yellow]⚠️ No new data to merge[/yellow]")
    return 0


def save_compression_interaction(output_path: str, prompt: str, response: str, is_mock: bool = False):
    """Save table compression LLM interaction records to a JSON file."""
    try:
        # Create an interaction record
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": "table_compression",
            "is_mock_response": is_mock,
            "input_prompt": prompt if prompt is not None else "",
            "llm_response": response if response is not None else "",
            "prompt_length": len(prompt) if prompt is not None else 0,
            "response_length": len(response) if response is not None else 0
        }

        # Save to a JSON file in the output directory
        interaction_file = os.path.join(output_path, "table_compression_interactions.json")

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
        logging.error(f"Failed to save table compression LLM interaction record: {e}")
        return None


def save_compression_operations_analysis(output_path: str, llm_response: str,
                                         operations: list, execution_results: list) -> Optional[str]:
    """Save table compression operation analysis results to a file."""
    try:
        # Create an operation analysis record
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
        operations_file = os.path.join(output_path, "table_compression_operations_analysis.json")

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
        logging.error(f"Failed to save table compression operation analysis: {e}")
        return None


def main():
    """Table compression main program entry point - batch processing mode."""
    console = Console()

    # Display welcome message
    console.print(Panel.fit(
        "🗜️ Large Language Model Tabular Memory System - Batch Table Compression Mode",
        style="bold blue"
    ))

    try:
        # Set up the compression environment
        output_path, project_folder = setup_compression_environment()
        console.print(f"📁 Created compression output project: {project_folder}")
        console.print(f"✅ Output directory is ready: {output_path}")

        # Get input and output directories
        input_tables_dir = get_input_tables_dir()
        output_tables_dir = os.path.join(output_path, "tables")

        # Check and convert JSON data (if table_data.json exists)
        data_dir = os.path.dirname(input_tables_dir)  # data directory
        json_converted = check_and_convert_json_data(data_dir, console)

        if json_converted:
            console.print(f"[green]✅ Table files have been updated from table_data.json[/green]")

        # Check if the input tables directory exists
        if not os.path.exists(input_tables_dir):
            console.print(f"[red]❌ Input tables directory not found: {input_tables_dir}[/red]")
            console.print(f"Please make sure you have table files to process in the {input_tables_dir} directory")
            return

        # Back up the input tables
        console.print(f"[yellow]📋 Backing up input tables...[/yellow]")
        backup_dir = backup_input_tables(input_tables_dir, output_path)
        console.print(f"[green]✅ Tables backed up to: {backup_dir}[/green]")

        # Initialize the LLM client
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
                console.print(f"[green]✅ Gemini API client is ready (using {len(GEMINI_API_KEYS)} API keys in rotation mode)[/green]")

        # Configure batch processing parameters
        TARGET_TABLE_INDEX = 4  # Index of important_events_table.csv

        # First, copy other tables to the output directory (except the one to be compressed)
        copy_non_target_tables(input_tables_dir, output_tables_dir, TARGET_TABLE_INDEX, console)

        # Import batch processing parameters from the configuration file
        from config import BATCH_SIZE, OVERLAP_SIZE

        # Check if the target table exists
        from src.table_schemas import TABLE_SCHEMAS
        target_schema = TABLE_SCHEMAS[TARGET_TABLE_INDEX]
        target_file = os.path.join(input_tables_dir, target_schema['file_name'])

        if not os.path.exists(target_file):
            console.print(f"[red]❌ Target table file not found: {target_file}[/red]")
            return

        # Read the target table to get the total number of rows
        import pandas as pd
        df = pd.read_csv(target_file, encoding='utf-8-sig')
        total_rows = len(df)

        console.print(f"[blue]📊 Target table: {target_schema['name']}[/blue]")
        console.print(f"[blue]📊 Total rows: {total_rows}[/blue]")
        console.print(f"[blue]📊 Batch size: {BATCH_SIZE}[/blue]")
        console.print(f"[blue]📊 Overlap size: {OVERLAP_SIZE}[/blue]")

        # Calculate the total number of batches
        step_size = BATCH_SIZE - OVERLAP_SIZE  # Step size for each iteration
        total_batches = ((total_rows - OVERLAP_SIZE - 1) // step_size) + 1

        console.print(f"[blue]📊 Planned batches to process: {total_batches}[/blue]")
        console.print(f"[blue]📊 Step size per batch: {step_size}[/blue]")

        # Display a preview of the queue format
        console.print(f"[blue]📊 Queue format preview:[/blue]")
        for preview_batch in range(min(3, total_batches)):
            preview_start = preview_batch * step_size
            preview_end = min(preview_start + BATCH_SIZE, total_rows)
            overlap_info = f"(overlap {OVERLAP_SIZE} rows)" if preview_batch > 0 else "(first batch)"
            console.print(f"[blue]  Batch {preview_batch + 1}: Rows {preview_start + 1}-{preview_end} (total {preview_end - preview_start} rows) {overlap_info}[/blue]")
        if total_batches > 3:
            console.print(f"[blue]  ... and {total_batches - 3} more batches[/blue]")

        # Start batch processing
        with Progress() as progress:
            task = progress.add_task("[green]Processing table compression...", total=total_batches)

            for batch_num in range(total_batches):
                start_row = batch_num * step_size
                end_row = min(start_row + BATCH_SIZE, total_rows)
                actual_batch_size = end_row - start_row

                progress.update(task, description=f"[green]Processing batch {batch_num + 1}/{total_batches} (Rows {start_row + 1}-{end_row})")

                console.print(f"\n[bold blue]🔄 Processing batch {batch_num + 1}/{total_batches}[/bold blue]")
                console.print(f"[cyan]📝 Processing row range: {start_row + 1} to {end_row} (total {actual_batch_size} rows)[/cyan]")

                try:
                    # Create the batch table manager
                    batch_table_manager, _, batch_df, temp_dir = create_batch_table_manager(
                        input_tables_dir, output_tables_dir, TARGET_TABLE_INDEX, start_row, BATCH_SIZE,
                        is_first_batch=(batch_num == 0)
                    )

                    # Create the prompt handler
                    prompt_handler = PromptManager(batch_table_manager)

                    # Use the same prompt generation logic as chat_to_table.py, but with MEMORY_TABLE_PROMPT_INTEGRATION
                    # Pass input_tables_dir to get the full data of other tables
                    compression_prompt = prompt_handler.generate_prompt_with_tables("", "", 0, use_integration_prompt=True, input_tables_dir=input_tables_dir, batch_df=batch_df)
                    console.print(f"[cyan]💬 Batch {batch_num + 1}/{total_batches} prompt length: {len(compression_prompt)} characters[/cyan]")

                    # Call the LLM for table compression
                    console.print(f"[yellow]🤖 Calling LLM to process batch {batch_num + 1}...[/yellow]")

                    if llm_client.is_available():
                        # Use the real API
                        llm_response = llm_client.generate_content(compression_prompt)
                        is_mock = False
                        console.print(f"[green]✅ Received LLM response for batch {batch_num + 1}[/green]")
                    else:
                        # Use a mock response (can keep the existing mock response method)
                        llm_response = prompt_handler.simulate_compression_response()
                        is_mock = True
                        console.print(f"[yellow]✅ Received mock LLM response for batch {batch_num + 1}[/yellow]")

                    # Save the LLM interaction record
                    interaction_file = save_compression_interaction(
                        output_path,
                        f"Batch {batch_num + 1}:\n{compression_prompt}",
                        llm_response if llm_response is not None else "",
                        is_mock
                    )

                    if llm_response:
                        # Extract and execute table operations (consistent with chat_to_table.py)
                        operations = prompt_handler.extract_table_operations(llm_response)

                        if operations:
                            console.print(f"[yellow]📋 Parsed {len(operations)} table operations for batch {batch_num + 1}[/yellow]")
                            for i, op in enumerate(operations, 1):
                                console.print(f"  {i}. {op}")

                            # Execute operations (consistent with chat_to_table.py)
                            execution_results = prompt_handler.execute_operations(operations)
                            success_count = sum(execution_results)
                            console.print(f"[green]✅ Successfully executed {success_count}/{len(operations)} operations for batch {batch_num + 1}[/green]")

                            # Get the processed data and merge it back into the main table
                            processed_df = batch_table_manager.load_table(TARGET_TABLE_INDEX)
                            console.print(f"[blue]📊 Processed data rows for batch {batch_num + 1}: {len(processed_df)}[/blue]")
                            if len(processed_df) > 0:
                                console.print(f"[blue]📊 Processed data preview for batch {batch_num + 1}:[/blue]")
                                for idx, row in processed_df.head(3).iterrows():
                                    console.print(f"  Row {idx}: {dict(row)}")

                            actual_processed = merge_batch_results(
                                input_tables_dir, output_tables_dir, TARGET_TABLE_INDEX, start_row, processed_df, console,
                                is_first_batch=(batch_num == 0)
                            )

                            console.print(f"[green]✅ Merged {actual_processed} rows from batch {batch_num + 1} into the main table[/green]")

                            # Save the operation analysis results
                            operations_file = save_compression_operations_analysis(
                                output_path, f"Batch {batch_num + 1}:\n{llm_response}", operations, execution_results
                            )

                        else:
                            console.print(f"[yellow]⚠️ No table operations parsed for batch {batch_num + 1}[/yellow]")

                            # Save the analysis record even if there are no operations (consistent with chat_to_table.py)
                            operations_file = save_compression_operations_analysis(
                                output_path, f"Batch {batch_num + 1}:\n{llm_response}", [], []
                            )

                    else:
                        console.print(f"[red]❌ LLM response generation failed for batch {batch_num + 1}[/red]")

                except Exception as e:
                    console.print(f"[red]❌ Failed to process batch {batch_num + 1}: {e}[/red]")
                    logging.error(f"Error processing batch {batch_num + 1}: {e}")
                finally:
                    # Clean up the temporary directory
                    if 'temp_dir' in locals() and os.path.exists(temp_dir):
                        import shutil
                        try:
                            shutil.rmtree(temp_dir)
                        except:
                            pass

                progress.advance(task)

        # Display the final results
        console.print(f"\n[bold green]🎉 Batch table compression complete![/bold green]")
        console.print(f"[bold green]Processed a total of {total_batches} batches[/bold green]")
        console.print(f"[bold green]Compression results saved in: {output_path}[/bold green]")
        console.print(f"[bold green]Backup files saved in: {backup_dir}[/bold green]")

        # Display statistics for the compressed table
        if os.path.exists(os.path.join(output_tables_dir, target_schema['file_name'])):
            final_df = pd.read_csv(os.path.join(output_tables_dir, target_schema['file_name']), encoding='utf-8-sig')
            final_rows = len(final_df)
            compression_ratio = (total_rows - final_rows) / total_rows * 100 if total_rows > 0 else 0

            console.print(f"\n[bold blue]📊 Compression Statistics:[/bold blue]")
            console.print(f"[cyan]Original rows: {total_rows}[/cyan]")
            console.print(f"[cyan]Compressed rows: {final_rows}[/cyan]")
            console.print(f"[cyan]Compression ratio: {compression_ratio:.2f}%[/cyan]")
            
            # Execute table processing, convert to JSON format
            console.print(f"\n[bold blue]📊 Starting table data conversion...[/bold blue]")
            try:
                from process_tables import process_tables_in_directory
                
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
        console.print(f"[red]❌ An error occurred during table compression: {e}[/red]")
        logging.error(f"Table compression error: {e}")
        import traceback
        traceback.print_exc()


def show_table_summary(tables_dir: str, console: Console):
    """Display table summary information."""
    try:
        from src.table_schemas import TABLE_SCHEMAS
        import pandas as pd

        summary_table = Table(title="📊 Table Data Summary")
        summary_table.add_column("Table", style="cyan")
        summary_table.add_column("Rows", style="green")
        summary_table.add_column("Status", style="yellow")

        for i, schema in TABLE_SCHEMAS.items():
            try:
                table_file = os.path.join(tables_dir, schema['file_name'])
                if os.path.exists(table_file):
                    df = pd.read_csv(table_file, encoding='utf-8-sig')
                    row_count = len(df)
                    status = "Has data" if row_count > 0 else "Empty table"
                else:
                    row_count = 0
                    status = "File not found"

                summary_table.add_row(f"{i}: {schema['name']}", str(row_count), status)
            except Exception as e:
                summary_table.add_row(f"{i}: {schema['name']}", "Error", str(e))

        console.print(summary_table)
        console.print()

    except Exception as e:
        console.print(f"[red]❌ Could not display table summary: {e}[/red]")


if __name__ == "__main__":
    main()
