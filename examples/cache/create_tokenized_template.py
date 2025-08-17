#!/usr/bin/env python3
"""
Script to create tokenized templates from consolidated actions and original prompt.

This script extracts all unique text values from actions, creates generic tokens (var1, var2, etc.),
and generates tokenized versions of both the actions and the prompt for templating.

Usage:
    python create_tokenized_template.py --actions consolidated_actions.json --prompt original_prompt.md
"""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def extract_text_values_from_actions(actions: List[Dict]) -> List[str]:
    """Extract all text values from actions that have text fields."""
    text_values = []
    
    for action in actions:
        # Extract from input_text actions
        if "input_text" in action and "text" in action["input_text"]:
            text = action["input_text"]["text"]
            if text:  # Skip empty strings
                text_values.append(text)
        
        # Extract from select_dropdown_option actions
        elif "select_dropdown_option" in action and "text" in action["select_dropdown_option"]:
            text = action["select_dropdown_option"]["text"]
            if text:  # Skip empty strings
                text_values.append(text)
        
        # Extract from any other action types that might have text fields
        # This covers future action types we might encounter
        else:
            for action_type, action_data in action.items():
                if isinstance(action_data, dict) and "text" in action_data:
                    text = action_data["text"]
                    if text and action_type not in ["input_text", "select_dropdown_option"]:
                        text_values.append(text)
    
    return text_values


def should_tokenize(value: str) -> bool:
    """Determine if a text value should be tokenized (i.e., is it variable data)."""
    # Skip common non-variable values
    skip_values = {
        "demo", "", " ", "test", "click", "submit", "next", "continue",
        "login", "register", "sign in", "sign up"
    }
    
    # Skip very short values that are likely UI elements
    if len(value.strip()) <= 1:
        return False
        
    # Skip common words/phrases
    if value.lower().strip() in skip_values:
        return False
        
    return True


def create_token_mapping(text_values: List[str]) -> Dict[str, str]:
    """Create mapping from generic tokens (var1, var2, etc.) to actual values."""
    # Get unique values and filter
    unique_values = []
    seen = set()
    
    for value in text_values:
        if value not in seen and should_tokenize(value):
            unique_values.append(value)
            seen.add(value)
    
    # Create token mapping
    token_mapping = {}
    for i, value in enumerate(unique_values, 1):
        token_mapping[f"var{i}"] = value
    
    return token_mapping


def tokenize_actions(actions: List[Dict], token_mapping: Dict[str, str]) -> List[Dict]:
    """Replace text values in actions with tokens."""
    # Create reverse mapping (value -> token)
    value_to_token = {v: k for k, v in token_mapping.items()}
    
    tokenized_actions = []
    
    for action in actions:
        tokenized_action = action.copy()
        
        # Handle input_text actions
        if "input_text" in action and "text" in action["input_text"]:
            original_text = action["input_text"]["text"]
            
            if original_text in value_to_token:
                # Replace with token
                tokenized_action["input_text"] = action["input_text"].copy()
                tokenized_action["input_text"]["text"] = f"{{{value_to_token[original_text]}}}"
        
        # Handle select_dropdown_option actions
        elif "select_dropdown_option" in action and "text" in action["select_dropdown_option"]:
            original_text = action["select_dropdown_option"]["text"]
            
            if original_text in value_to_token:
                # Replace with token
                tokenized_action["select_dropdown_option"] = action["select_dropdown_option"].copy()
                tokenized_action["select_dropdown_option"]["text"] = f"{{{value_to_token[original_text]}}}"
        
        # Handle any other action types with text fields
        else:
            for action_type, action_data in action.items():
                if isinstance(action_data, dict) and "text" in action_data:
                    original_text = action_data["text"]
                    
                    if original_text in value_to_token:
                        tokenized_action[action_type] = action_data.copy()
                        tokenized_action[action_type]["text"] = f"{{{value_to_token[original_text]}}}"
        
        tokenized_actions.append(tokenized_action)
    
    return tokenized_actions


def tokenize_prompt(prompt_content: str, token_mapping: Dict[str, str]) -> str:
    """Replace values in prompt with tokens."""
    tokenized_prompt = prompt_content
    
    # Create reverse mapping (value -> token)
    value_to_token = {v: k for k, v in token_mapping.items()}
    
    # Sort by length (longest first) to avoid partial replacements
    # This prevents shorter values from breaking longer tokens
    sorted_values = sorted(value_to_token.keys(), key=len, reverse=True)
    
    for value in sorted_values:
        token = value_to_token[value]
        # Use word boundary replacement to avoid partial matches
        # But for exact string replacement, we need to be more careful
        
        # First, let's do exact replacement but avoid replacing inside existing tokens
        if value in tokenized_prompt:
            # Split on existing tokens to avoid replacing inside them
            parts = []
            remaining = tokenized_prompt
            
            while value in remaining:
                before, match, after = remaining.partition(value)
                
                # Check if this match is inside a token (between { and })
                # Count open braces before this position
                open_braces = before.count('{') - before.count('}')
                
                if open_braces <= 0:  # Not inside a token
                    parts.append(before)
                    parts.append(f"{{{token}}}")
                    remaining = after
                else:  # Inside a token, don't replace
                    parts.append(before + match)
                    remaining = after
            
            parts.append(remaining)
            tokenized_prompt = ''.join(parts)
    
    return tokenized_prompt


def main():
    parser = argparse.ArgumentParser(description="Create tokenized templates from actions and prompt")
    parser.add_argument("--actions", required=True, help="Path to consolidated actions JSON file")
    parser.add_argument("--prompt", required=True, help="Path to original prompt markdown file")
    parser.add_argument("--output-dir", default=".", help="Output directory for tokenized files")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    actions_path = Path(args.actions)
    prompt_path = Path(args.prompt)
    output_dir = Path(args.output_dir)
    
    if not actions_path.exists():
        print(f"❌ Actions file not found: {actions_path}")
        return 1
        
    if not prompt_path.exists():
        print(f"❌ Prompt file not found: {prompt_path}")
        return 1
    
    # Load actions
    print(f"📄 Loading actions from: {actions_path}")
    with open(actions_path, 'r') as f:
        actions = json.load(f)
    
    # Load prompt
    print(f"📄 Loading prompt from: {prompt_path}")
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Extract text values from actions
    print("🔍 Extracting text values from actions...")
    text_values = extract_text_values_from_actions(actions)
    
    if args.verbose:
        print(f"   Found {len(text_values)} total text values")
        print(f"   Unique values: {len(set(text_values))}")
    
    # Create token mapping
    print("🏷️  Creating token mapping...")
    token_mapping = create_token_mapping(text_values)
    
    print(f"📊 Created {len(token_mapping)} tokens:")
    for token, value in token_mapping.items():
        print(f"   {token}: '{value}'")
    
    # Tokenize actions
    print("🔄 Tokenizing actions...")
    tokenized_actions = tokenize_actions(actions, token_mapping)
    
    # Tokenize prompt
    print("🔄 Tokenizing prompt...")
    tokenized_prompt = tokenize_prompt(prompt_content, token_mapping)
    
    # Generate output filenames
    actions_stem = actions_path.stem
    prompt_stem = prompt_path.stem
    
    tokenized_actions_path = output_dir / f"tokenized_{actions_stem}.json"
    tokenized_prompt_path = output_dir / f"tokenized_{prompt_stem}.md"
    token_mapping_path = output_dir / f"{actions_stem}_token_mapping.json"
    
    # Save tokenized actions
    print(f"💾 Saving tokenized actions to: {tokenized_actions_path}")
    with open(tokenized_actions_path, 'w') as f:
        json.dump(tokenized_actions, f, indent=2)
    
    # Save tokenized prompt
    print(f"💾 Saving tokenized prompt to: {tokenized_prompt_path}")
    with open(tokenized_prompt_path, 'w') as f:
        f.write(tokenized_prompt)
    
    # Save token mapping for reference
    print(f"💾 Saving token mapping to: {token_mapping_path}")
    with open(token_mapping_path, 'w') as f:
        json.dump(token_mapping, f, indent=2)
    
    print("✅ Tokenization completed successfully!")
    print(f"   📁 Generated files:")
    print(f"      • {tokenized_actions_path}")
    print(f"      • {tokenized_prompt_path}")
    print(f"      • {token_mapping_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
