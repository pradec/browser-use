#!/usr/bin/env python3
"""
Extract actions from Markdown LLM logs and combine into a single JSON array.

Simple approach:
1. Read each .md file chronologically (by modification time)
2. Find the ## Response section
3. Parse the JSON content in that section
4. Extract $.content.action using simple dict navigation
5. Combine all actions in chronological order
6. Write consolidated_actions.json
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract actions from Markdown logs")
    parser.add_argument("--logs-dir", required=True, help="Directory containing .md files")
    parser.add_argument("--out", help="Output file (default: logs-dir/consolidated_actions.json)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser.parse_args()


def extract_response_json(md_content: str) -> Optional[dict]:
    """Extract JSON from ## Response section."""
    # Find ## Response section
    response_match = re.search(r'^## Response\s*$', md_content, re.MULTILINE | re.IGNORECASE)
    if not response_match:
        return None
    
    start = response_match.end()
    
    # Find next ## section or end of file
    next_section = re.search(r'^##\s+', md_content[start:], re.MULTILINE)
    if next_section:
        end = start + next_section.start()
    else:
        end = len(md_content)
    
    response_section = md_content[start:end]
    
    # Find JSON content (look for first { and extract until matching })
    first_brace = response_section.find('{')
    if first_brace == -1:
        return None
    
    # Extract JSON using bracket counting
    json_text = extract_json_object(response_section, first_brace)
    if not json_text:
        return None
    
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # Try to fix common issues with newlines in strings
        fixed_json = fix_json_newlines(json_text)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            return None


def extract_json_object(text: str, start_pos: int) -> Optional[str]:
    """Extract a complete JSON object starting from start_pos."""
    if start_pos >= len(text) or text[start_pos] != '{':
        return None
    
    brace_count = 0
    in_string = False
    escape_next = False
    i = start_pos
    
    while i < len(text):
        char = text[i]
        
        if escape_next:
            escape_next = False
            i += 1
            continue
        
        if char == '\\':
            escape_next = True
            i += 1
            continue
        
        if char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_pos:i+1]
        
        i += 1
    
    return None


def fix_json_newlines(json_text: str) -> str:
    """Fix JSON where strings contain literal newlines instead of \\n."""
    result = []
    in_string = False
    escape_next = False
    
    for char in json_text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            result.append(char)
            continue
        
        if char == '"':
            in_string = not in_string
            result.append(char)
        elif in_string and char == '\n':
            result.append('\\n')
        elif in_string and char == '\r':
            result.append('\\r')
        else:
            result.append(char)
    
    return ''.join(result)


def extract_actions(response_json: dict) -> List[dict]:
    """Extract actions using $.content.action selector."""
    if not isinstance(response_json, dict):
        return []
    
    content = response_json.get('content')
    if not isinstance(content, dict):
        return []
    
    action = content.get('action')
    if not action:
        return []
    
    # Handle both single action (dict) and multiple actions (list)
    if isinstance(action, dict):
        return [action]
    elif isinstance(action, list):
        return [a for a in action if isinstance(a, dict)]
    else:
        return []


def main():
    args = parse_args()
    
    logs_dir = Path(args.logs_dir).resolve()
    if not logs_dir.is_dir():
        print(f"Error: Directory not found: {logs_dir}")
        return 1
    
    # Find all .md files and sort by modification time (chronological)
    md_files = [f for f in logs_dir.glob("*.md") if f.is_file()]
    md_files.sort(key=lambda f: f.stat().st_mtime)
    
    if not md_files:
        print(f"No .md files found in {logs_dir}")
        return 1
    
    if args.verbose:
        print(f"Found {len(md_files)} .md files")
    
    all_actions = []
    
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            response_json = extract_response_json(content)
            
            if response_json:
                actions = extract_actions(response_json)
                all_actions.extend(actions)
                
                if args.verbose:
                    print(f"{md_file.name}: +{len(actions)} actions (total: {len(all_actions)})")
            else:
                if args.verbose:
                    print(f"{md_file.name}: +0 actions (no valid JSON in Response section)")
        
        except Exception as e:
            if args.verbose:
                print(f"Error reading {md_file.name}: {e}")
            continue
    
    # Write output
    if args.out:
        output_path = Path(args.out)
    else:
        output_path = logs_dir / "consolidated_actions.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_actions, f, indent=2, ensure_ascii=False)
    
    print(f"Wrote {len(all_actions)} actions to {output_path}")
    return 0


if __name__ == "__main__":
    exit(main())
