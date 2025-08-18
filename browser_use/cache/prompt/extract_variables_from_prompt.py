#!/usr/bin/env python3
"""
Step 2A: Extract variables from new prompt using tokenized template.

This script takes a tokenized prompt template and a new prompt, then extracts
variable values by matching the template structure against the new content.

Usage:
    python extract_variables_from_prompt.py --template tokenized_prompt.md --new-prompt new_prompt.md --output new_values.json
"""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from task_logger import get_logger


def parse_template_line(template_line: str) -> Tuple[Optional[str], List[str]]:
    """
    Parse a template line and extract the pattern and tokens.
    
    Example:
        "Name: {var1} {var2}" -> ("Name: (.*?) (.*?)$", ["var1", "var2"])
        "Date of Birth: {var3}. Return this exact text." -> ("Date of Birth: (.*?)\\. Return this exact text\\.$", ["var3"])
    """
    # Find all tokens like {var1}, {var2}, etc.
    tokens = re.findall(r'\{(var\d+)\}', template_line)
    
    if not tokens:
        return None, []
    
    # Escape special regex characters except our tokens
    pattern = re.escape(template_line)
    
    # Replace escaped tokens with capture groups
    for token in tokens:
        escaped_token = re.escape(f"{{{token}}}")
        pattern = pattern.replace(escaped_token, "(.*?)")
    
    # Add end-of-line anchor
    pattern = pattern + "$"
    
    return pattern, tokens


def extract_variables_from_prompts(template_content: str, new_content: str, logger) -> Dict[str, str]:
    """Extract variables by matching template against new prompt."""
    variables = {}
    
    template_lines = template_content.strip().split('\n')
    new_lines = new_content.strip().split('\n')
    
    # Create a lookup for new lines (case-insensitive for robustness)
    new_lines_lookup = {line.strip().lower(): line.strip() for line in new_lines if line.strip()}
    
    for template_line in template_lines:
        template_line = template_line.strip()
        if not template_line or '{var' not in template_line:
            continue
            
        pattern, tokens = parse_template_line(template_line)
        if not pattern or not tokens:
            continue
            
        logger.info(f"🔍 Processing template: '{template_line}'")
        logger.debug(f"   Pattern: {pattern}")
        logger.debug(f"   Tokens: {tokens}")
        
        # Try to find matching line in new prompt
        found_match = False
        for new_line in new_lines:
            new_line = new_line.strip()
            if not new_line:
                continue
                
            match = re.match(pattern, new_line, re.IGNORECASE)
            if match:
                logger.success(f"Matched: '{new_line}'")
                
                # Extract values for each token
                for i, token in enumerate(tokens):
                    value = match.group(i + 1).strip()
                    variables[token] = value
                    logger.info(f"      {token} = '{value}'")
                
                found_match = True
                break
        
        if not found_match:
            logger.warning(f"No match found for template line")
    
    return variables


def main():
    parser = argparse.ArgumentParser(description="Extract variables from new prompt using tokenized template")
    parser.add_argument("--template", required=True, help="Path to tokenized prompt template (.md)")
    parser.add_argument("--new-prompt", required=True, help="Path to new prompt with different values (.md)")
    parser.add_argument("--output", required=True, help="Output path for extracted variables (.json)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--run-dir", help="Run directory for logging (optional)")
    
    args = parser.parse_args()
    
    # Initialize logger
    if args.run_dir:
        run_dir = Path(args.run_dir)
        logger = get_logger("extract_variables_from_prompt", run_dir)
    else:
        logger = get_logger("extract_variables_from_prompt")
    
    template_path = Path(args.template)
    new_prompt_path = Path(args.new_prompt)
    output_path = Path(args.output)
    
    if not template_path.exists():
        logger.error(f"Template file not found: {template_path}")
        return 1
        
    if not new_prompt_path.exists():
        logger.error(f"New prompt file not found: {new_prompt_path}")
        return 1
    
    # Load template
    logger.file_operation("loading template", template_path)
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Load new prompt
    logger.file_operation("loading new prompt", new_prompt_path)
    with open(new_prompt_path, 'r') as f:
        new_content = f.read()
    
    if args.verbose:
        logger.info("📋 Template content:")
        for i, line in enumerate(template_content.split('\n'), 1):
            if '{var' in line:
                logger.info(f"   {i}: {line}")
        
        logger.info("📋 New prompt content:")
        for i, line in enumerate(new_content.split('\n'), 1):
            logger.info(f"   {i}: {line}")
    
    # Extract variables
    logger.info("🔍 Extracting variables...")
    variables = extract_variables_from_prompts(template_content, new_content, logger)
    
    logger.statistics({
        f"Extracted variables": len(variables)
    })
    
    for token, value in variables.items():
        logger.info(f"   {token}: '{value}'")
    
    # Save results
    logger.file_operation("saving variables", output_path)
    with open(output_path, 'w') as f:
        json.dump(variables, f, indent=2)
    
    logger.success("Variable extraction completed successfully!")
    logger.statistics({
        "Output file": str(output_path),
        "Variables extracted": len(variables)
    })
    
    # Save execution summary
    summary_data = {
        "template_file": str(template_path),
        "new_prompt_file": str(new_prompt_path),
        "output_file": str(output_path),
        "variables_extracted": len(variables),
        "variables": variables,
        "success": True
    }
    logger.save_execution_summary(summary_data)
    
    return 0


if __name__ == "__main__":
    exit(main())
