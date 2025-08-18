#!/usr/bin/env python3
"""
Smart caching controller for Browser Use tasks.

This script implements intelligent caching for prompt-based tasks:
1. Reads task name from prompt file (first line)
2. Checks for cached execution plan
3. If cached, extracts variables and executes using cached actions
4. If not cached, executes with LLM and creates cache

Cache Structure:
~/.cache/browseruse/tasks/{task_name}/
├── consolidated_actions.json
├── tokenized_consolidated_actions.json
├── tokenized_preauth_request.md
└── consolidated_actions_token_mapping.json

Usage:
    python run_task_with_cache.py --prompt path/to/prompt.md [other options]
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from task_logger import get_logger, set_run_directory


def get_cache_base_directory() -> Path:
    """Get the consistent cache base directory."""
    # Use ~/.cache/browseruse for consistency
    cache_home = Path.home() / '.cache' / 'browseruse'
    cache_home.mkdir(parents=True, exist_ok=True)
    return cache_home


def extract_task_name_from_prompt(prompt_path: Path) -> str:
    """
    Extract task name from first line of prompt file.
    
    Process:
    1. Read first line
    2. Remove # from beginning if exists
    3. Trim whitespace from both ends
    4. Replace spaces with underscores
    5. Convert to lowercase
    
    Example: "# Preauthorization Request Task" -> "preauthorization_request_task"
    """
    with open(prompt_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    
    # Remove # from beginning
    if first_line.startswith('#'):
        first_line = first_line[1:].strip()
    
    # Replace spaces with underscores and convert to lowercase
    task_name = re.sub(r'\s+', '_', first_line.lower())
    
    # Remove any non-alphanumeric characters except underscores
    task_name = re.sub(r'[^a-z0-9_]', '', task_name)
    
    return task_name


def get_task_cache_directory(task_name: str) -> Path:
    """Get the cache directory for a specific task."""
    cache_base = get_cache_base_directory()
    task_cache_dir = cache_base / 'tasks' / task_name
    return task_cache_dir


def check_cache_exists(task_cache_dir: Path) -> bool:
    """Check if a complete cache exists for the task."""
    required_files = [
        'consolidated_actions.json',
        'tokenized_consolidated_actions.json',
        'tokenized_preauth_request.md',  # This should be dynamic based on prompt name
        'consolidated_actions_token_mapping.json'
    ]
    
    return all((task_cache_dir / file).exists() for file in required_files)


def run_command(cmd: List[str], cwd: Optional[Path] = None, description: str = "", logger=None) -> bool:
    """Run a command and return success status."""
    if logger:
        logger.command(' '.join(cmd), description)
    else:
        print(f"🔧 {description}")
        print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        if logger:
            logger.command_result(True, result.stdout)
        else:
            print(f"   ✅ Success")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if logger:
            logger.command_result(False, e.stdout, e.stderr)
        else:
            print(f"   ❌ Failed: {e}")
            if e.stdout:
                print(f"   Stdout: {e.stdout}")
            if e.stderr:
                print(f"   Stderr: {e.stderr}")
        return False


def execute_with_llm_and_cache(
    prompt_path: Path, 
    task_name: str, 
    task_cache_dir: Path, 
    domain: str,
    model: str,
    other_args: List[str],
    logger
) -> bool:
    """Execute task with LLM and create cache artifacts."""
    logger.info(f"🤖 Cache miss - executing with LLM for task: {task_name}")
    
    # Get the directory containing our scripts
    script_dir = Path(__file__).parent
    
    # Step 1: Run the original task with LLM
    logger.step(1, "Running task with LLM...")
    run_task_cmd = [
        sys.executable, str(script_dir / 'run_task.py'),
        '--prompt', str(prompt_path),
        '--domain', domain,
        '--model', model,
        '--run-dir', str(logger.run_directory)  # Pass run directory to run_task
    ]
    
    # Filter other_args to only include what run_task.py supports
    for arg in other_args:
        if arg in ['--headless']:
            run_task_cmd.append(arg)
        elif arg == '--wait':
            # Find the next argument which should be the wait value
            wait_idx = other_args.index(arg)
            if wait_idx + 1 < len(other_args):
                run_task_cmd.extend([arg, other_args[wait_idx + 1]])
    
    if not run_command(run_task_cmd, description=f"Executing task with LLM", logger=logger):
        logger.error("Failed to execute task with LLM")
        return False
    
    # Find the generated llm_calls directory in /var/folders
    # The run_task.py should have created a temp directory with llm_calls
    # We need to find the most recent one
    temp_base = Path(tempfile.gettempdir())
    browser_use_dirs = list(temp_base.glob('browser_use_agent_*'))
    if not browser_use_dirs:
        logger.error("No browser_use_agent directories found in temp")
        return False
    
    # Get the most recent one
    latest_agent_dir = max(browser_use_dirs, key=lambda p: p.stat().st_mtime)
    llm_calls_dir = latest_agent_dir / 'llm_calls'
    
    if not llm_calls_dir.exists():
        logger.error(f"llm_calls directory not found in {latest_agent_dir}")
        return False
    
    logger.success(f"Found LLM calls directory: {llm_calls_dir}")
    
    # Step 2: Create consolidated actions from llm_calls
    logger.step(2, "Creating consolidated actions...")
    consolidated_actions_path = llm_calls_dir / 'consolidated_actions.json'
    
    combine_cmd = [
        sys.executable, str(script_dir / 'combine_actions_from_md.py'),
        '--logs-dir', str(llm_calls_dir),
        '--out', str(consolidated_actions_path),
        '--verbose',
        '--run-dir', str(logger.run_directory)  # Pass run directory
    ]
    
    if not run_command(combine_cmd, description="Combining actions from LLM logs", logger=logger):
        logger.error("Failed to create consolidated actions")
        return False
    
    # Step 3: Create task cache directory and copy/create cache artifacts
    logger.step(3, "Creating task cache directory...")
    task_cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy consolidated actions to cache
    cache_consolidated_path = task_cache_dir / 'consolidated_actions.json'
    cache_consolidated_path.write_text(consolidated_actions_path.read_text())
    logger.success(f"Copied consolidated actions to cache: {cache_consolidated_path}")
    
    # Step 4: Create tokenized template
    logger.step(4, "Creating tokenized template...")
    
    tokenize_cmd = [
        sys.executable, str(script_dir / 'create_tokenized_template.py'),
        '--actions', str(cache_consolidated_path),
        '--prompt', str(prompt_path),
        '--output-dir', str(task_cache_dir),
        '--verbose',
        '--run-dir', str(logger.run_directory)  # Pass run directory
    ]
    
    if not run_command(tokenize_cmd, description="Creating tokenized template", logger=logger):
        logger.error("Failed to create tokenized template")
        return False
    
    logger.success(f"Task cache created successfully for: {task_name}")
    logger.info(f"📁 Cache location: {task_cache_dir}")
    
    return True


def execute_from_cache(
    prompt_path: Path,
    task_name: str, 
    task_cache_dir: Path,
    domain: str,
    other_args: List[str],
    logger
) -> bool:
    """Execute task using cached artifacts."""
    logger.info(f"⚡ Cache hit - executing from cache for task: {task_name}")
    logger.info(f"📁 Cache location: {task_cache_dir}")
    
    # Get the directory containing our scripts
    script_dir = Path(__file__).parent
    
    # Find the tokenized prompt template (look for tokenized_*.md)
    tokenized_prompts = list(task_cache_dir.glob('tokenized_*.md'))
    if not tokenized_prompts:
        logger.error("No tokenized prompt template found in cache")
        return False
    
    tokenized_prompt_path = tokenized_prompts[0]  # Use the first one found
    
    # Step 1: Extract variables from the new prompt
    logger.step(1, "Extracting variables from prompt...")
    
    variables_path = task_cache_dir / 'extracted_variables.json'
    
    extract_cmd = [
        sys.executable, str(script_dir / 'extract_variables_from_prompt.py'),
        '--template', str(tokenized_prompt_path),
        '--new-prompt', str(prompt_path),
        '--output', str(variables_path),
        '--verbose',
        '--run-dir', str(logger.run_directory)  # Pass run directory
    ]
    
    if not run_command(extract_cmd, description="Extracting variables from prompt", logger=logger):
        logger.error("Failed to extract variables")
        return False
    
    # Step 2: Substitute tokens in actions
    logger.step(2, "Substituting tokens in actions...")
    
    tokenized_actions_path = task_cache_dir / 'tokenized_consolidated_actions.json'
    substituted_actions_path = task_cache_dir / 'substituted_actions.json'
    
    # Use the substitute script from cache prompt directory (moved from use-cases)
    substitute_cmd = [
        sys.executable, str(script_dir / 'substitute_tokens_in_actions.py'),
        '--template-actions', str(tokenized_actions_path),
        '--values', str(variables_path),
        '--output', str(substituted_actions_path),
        '--verbose',
        '--run-dir', str(logger.run_directory)  # Pass run directory
    ]
    
    if not run_command(substitute_cmd, description="Substituting tokens in actions", logger=logger):
        logger.error("Failed to substitute tokens")
        return False
    
    # Step 3: Execute the substituted actions
    logger.step(3, "Executing substituted actions...")
    
    execute_cmd = [
        sys.executable, str(script_dir / 'run_json_actions.py'),
        str(substituted_actions_path),
        '--url', domain,
        '--continue-on-error',
        '--verbose',
        '--run-dir', str(logger.run_directory)  # Pass run directory
    ]
    
    # Add any additional args that make sense for json execution
    filtered_args = []
    skip_next = False
    for i, arg in enumerate(other_args):
        if skip_next:
            skip_next = False
            continue
        if arg in ['--headless']:
            filtered_args.append(arg)
        elif arg.startswith('--delay'):
            filtered_args.append(arg)
            if '=' not in arg and i + 1 < len(other_args):
                filtered_args.append(other_args[i + 1])
                skip_next = True
    
    execute_cmd.extend(filtered_args)
    
    if not run_command(execute_cmd, description="Executing cached actions", logger=logger):
        logger.error("Failed to execute cached actions")
        return False
    
    logger.success(f"Task executed successfully from cache: {task_name}")
    
    return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Smart caching controller for Browser Use tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # First run - will execute with LLM and create cache
    python run_task_with_cache.py --prompt preauth_request.md --domain https://example.com --model gpt-4

    # Subsequent runs - will use cache if available
    python run_task_with_cache.py --prompt new_patient_request.md --domain https://example.com --model gpt-4
        """
    )
    
    parser.add_argument('--prompt', required=True, help='Path to prompt markdown file')
    parser.add_argument('--domain', default='https://mellow-belekoy-b56ebb.netlify.app/', help='Domain URL to execute against')
    parser.add_argument('--model', default='gpt-4o', help='LLM model to use')
    parser.add_argument('--force-cache-rebuild', action='store_true', help='Force rebuild of cache even if it exists')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between actions')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()
    
    # Initialize logger first
    logger = get_logger("run_task_with_cache")
    
    prompt_path = Path(args.prompt).resolve()
    if not prompt_path.exists():
        logger.error(f"Prompt file not found: {prompt_path}")
        return 1
    
    logger.info(f"🚀 Browser Use Smart Cache Controller")
    logger.info(f"📄 Prompt file: {prompt_path}")
    
    # Extract task name from prompt
    task_name = extract_task_name_from_prompt(prompt_path)
    logger.info(f"🏷️  Task name: {task_name}")
    
    # Get task cache directory
    task_cache_dir = get_task_cache_directory(task_name)
    logger.info(f"📁 Cache directory: {task_cache_dir}")
    
    # Check if cache exists and is complete
    cache_exists = check_cache_exists(task_cache_dir) and not args.force_cache_rebuild
    
    if cache_exists:
        logger.success(f"Cache found for task: {task_name}")
    else:
        if args.force_cache_rebuild:
            logger.info(f"🔄 Force rebuilding cache for task: {task_name}")
        else:
            logger.warning(f"No cache found for task: {task_name}")
    
    # Prepare additional arguments to pass through
    other_args = []
    if args.headless:
        other_args.append('--headless')
    if args.delay != 1.0:
        other_args.extend(['--wait', str(args.delay)])
    # Note: run_task.py doesn't support --verbose, so we skip it
    
    # Execute based on cache status
    if cache_exists:
        success = execute_from_cache(
            prompt_path=prompt_path,
            task_name=task_name,
            task_cache_dir=task_cache_dir,
            domain=args.domain,
            other_args=other_args,
            logger=logger
        )
    else:
        success = execute_with_llm_and_cache(
            prompt_path=prompt_path,
            task_name=task_name,
            task_cache_dir=task_cache_dir,
            domain=args.domain,
            model=args.model,
            other_args=other_args,
            logger=logger
        )
    
    if success:
        logger.success(f"Task completed successfully!")
        logger.statistics({
            "Task": task_name,
            "Cache used": "Yes" if cache_exists else "No (cache created)",
            "Cache location": str(task_cache_dir),
            "Run directory": str(logger.run_directory)
        })
        
        # Save execution summary
        summary_data = {
            "task_name": task_name,
            "cache_used": cache_exists,
            "cache_location": str(task_cache_dir),
            "success": True,
            "execution_mode": "cache_hit" if cache_exists else "cache_miss_llm"
        }
        logger.save_execution_summary(summary_data)
        logger.create_run_summary()
        
        return 0
    else:
        logger.error(f"Task failed!")
        summary_data = {
            "task_name": task_name,
            "cache_used": cache_exists,
            "cache_location": str(task_cache_dir),
            "success": False,
            "execution_mode": "cache_hit" if cache_exists else "cache_miss_llm"
        }
        logger.save_execution_summary(summary_data)
        return 1


if __name__ == "__main__":
    exit(main())
