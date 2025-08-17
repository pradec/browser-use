#!/usr/bin/env python3
"""
Step 2B: Substitute tokens in actions with actual values.

This script takes tokenized actions and a values file, then replaces all
{var1}, {var2}, etc. tokens with the corresponding actual values.

Usage:
    python substitute_tokens_in_actions.py --template-actions tokenized_actions.json --values new_values.json --output substituted_actions.json
"""

import json
import argparse
import copy
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set


def substitute_tokens_in_action(action: Dict[str, Any], values: Dict[str, str]) -> Tuple[Dict[str, Any], int]:
    """Substitute tokens in a single action with actual values."""
    # Make a deep copy to avoid modifying the original
    substituted_action = copy.deepcopy(action)
    substitutions_made = 0
    
    # Handle input_text actions
    if "input_text" in action and "text" in action["input_text"]:
        text = action["input_text"]["text"]
        if text.startswith("{") and text.endswith("}"):
            token = text[1:-1]  # Remove { and }
            if token in values:
                substituted_action["input_text"]["text"] = values[token]
                substitutions_made += 1
    
    # Handle select_dropdown_option actions
    elif "select_dropdown_option" in action and "text" in action["select_dropdown_option"]:
        text = action["select_dropdown_option"]["text"]
        if text.startswith("{") and text.endswith("}"):
            token = text[1:-1]  # Remove { and }
            if token in values:
                substituted_action["select_dropdown_option"]["text"] = values[token]
                substitutions_made += 1
    
    # Handle any other action types with text fields
    else:
        for action_type, action_data in action.items():
            if isinstance(action_data, dict) and "text" in action_data:
                text = action_data["text"]
                if text.startswith("{") and text.endswith("}"):
                    token = text[1:-1]
                    if token in values:
                        substituted_action[action_type]["text"] = values[token]
                        substitutions_made += 1
    
    return substituted_action, substitutions_made


def substitute_tokens_in_actions(template_actions: List[Dict], values: Dict[str, str], verbose: bool = False) -> Tuple[List[Dict], int, Set[str], Set[str]]:
    """Substitute tokens in all actions."""
    substituted_actions = []
    total_substitutions = 0
    tokens_found = set()
    tokens_substituted = set()
    
    for i, action in enumerate(template_actions):
        substituted_action, substitutions_made = substitute_tokens_in_action(action, values)
        substituted_actions.append(substituted_action)
        total_substitutions += substitutions_made
        
        # Track tokens for reporting
        for action_type, action_data in action.items():
            if isinstance(action_data, dict) and "text" in action_data:
                text = action_data["text"]
                if text.startswith("{") and text.endswith("}"):
                    token = text[1:-1]
                    tokens_found.add(token)
                    if substitutions_made > 0:
                        tokens_substituted.add(token)
                        if verbose:
                            old_value = text
                            new_value = values.get(token, "NOT_FOUND")
                            print(f"   Action {i+1}: {old_value} → '{new_value}'")
    
    return substituted_actions, total_substitutions, tokens_found, tokens_substituted


def main():
    parser = argparse.ArgumentParser(description="Substitute tokens in actions with actual values")
    parser.add_argument("--template-actions", required=True, help="Path to tokenized actions JSON file")
    parser.add_argument("--values", required=True, help="Path to values JSON file (token → value mapping)")
    parser.add_argument("--output", required=True, help="Output path for substituted actions JSON")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    template_path = Path(args.template_actions)
    values_path = Path(args.values)
    output_path = Path(args.output)
    
    if not template_path.exists():
        print(f"❌ Template actions file not found: {template_path}")
        return 1
        
    if not values_path.exists():
        print(f"❌ Values file not found: {values_path}")
        return 1
    
    # Load template actions
    print(f"📄 Loading template actions: {template_path}")
    with open(template_path, 'r') as f:
        template_actions = json.load(f)
    
    # Load values
    print(f"📄 Loading values: {values_path}")
    with open(values_path, 'r') as f:
        values = json.load(f)
    
    if args.verbose:
        print(f"\n📊 Template actions: {len(template_actions)} total actions")
        print(f"📊 Values available: {len(values)} tokens")
        print("📋 Available tokens:")
        for token, value in values.items():
            print(f"   {token}: '{value}'")
    
    # Perform substitutions
    print("\n🔄 Substituting tokens with values...")
    substituted_actions, total_substitutions, tokens_found, tokens_substituted = substitute_tokens_in_actions(
        template_actions, values, args.verbose
    )
    
    # Report results
    print(f"\n📊 Substitution Results:")
    print(f"   📁 Total actions processed: {len(template_actions)}")
    print(f"   🔍 Tokens found in actions: {len(tokens_found)}")
    print(f"   ✅ Tokens successfully substituted: {len(tokens_substituted)}")
    print(f"   🔄 Total substitutions made: {total_substitutions}")
    
    if tokens_found - tokens_substituted:
        print(f"   ⚠️  Tokens not substituted: {tokens_found - tokens_substituted}")
    
    # Save substituted actions
    print(f"\n💾 Saving substituted actions to: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(substituted_actions, f, indent=2)
    
    print("✅ Token substitution completed successfully!")
    print(f"   📁 Output file: {output_path}")
    print(f"   📊 Actions ready for execution: {len(substituted_actions)}")
    
    return 0


if __name__ == "__main__":
    exit(main())
