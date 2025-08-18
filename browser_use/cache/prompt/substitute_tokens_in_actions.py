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

from task_logger import get_logger


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


def substitute_tokens_in_actions(template_actions: List[Dict], values: Dict[str, str], logger, verbose: bool = False) -> Tuple[List[Dict], int, Set[str], Set[str]]:
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
                            logger.info(f"   Action {i+1}: {old_value} → '{new_value}'")
    
    return substituted_actions, total_substitutions, tokens_found, tokens_substituted


def main():
    parser = argparse.ArgumentParser(description="Substitute tokens in actions with actual values")
    parser.add_argument("--template-actions", required=True, help="Path to tokenized actions JSON file")
    parser.add_argument("--values", required=True, help="Path to values JSON file (token → value mapping)")
    parser.add_argument("--output", required=True, help="Output path for substituted actions JSON")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--run-dir", help="Run directory for logging (optional)")
    
    args = parser.parse_args()
    
    # Initialize logger
    if args.run_dir:
        run_dir = Path(args.run_dir)
        logger = get_logger("substitute_tokens_in_actions", run_dir)
    else:
        logger = get_logger("substitute_tokens_in_actions")
    
    template_path = Path(args.template_actions)
    values_path = Path(args.values)
    output_path = Path(args.output)
    
    if not template_path.exists():
        logger.error(f"Template actions file not found: {template_path}")
        return 1
        
    if not values_path.exists():
        logger.error(f"Values file not found: {values_path}")
        return 1
    
    # Load template actions
    logger.file_operation("loading template actions", template_path)
    with open(template_path, 'r') as f:
        template_actions = json.load(f)
    
    # Load values
    logger.file_operation("loading values", values_path)
    with open(values_path, 'r') as f:
        values = json.load(f)
    
    if args.verbose:
        logger.statistics({
            "Template actions": len(template_actions),
            "Values available": len(values)
        })
        logger.info("📋 Available tokens:")
        for token, value in values.items():
            logger.info(f"   {token}: '{value}'")
    
    # Perform substitutions
    logger.info("🔄 Substituting tokens with values...")
    substituted_actions, total_substitutions, tokens_found, tokens_substituted = substitute_tokens_in_actions(
        template_actions, values, logger, args.verbose
    )
    
    # Report results
    logger.statistics({
        "Total actions processed": len(template_actions),
        "Tokens found in actions": len(tokens_found),
        "Tokens successfully substituted": len(tokens_substituted),
        "Total substitutions made": total_substitutions
    })
    
    if tokens_found - tokens_substituted:
        logger.warning(f"Tokens not substituted: {tokens_found - tokens_substituted}")
    
    # Save substituted actions
    logger.file_operation("saving substituted actions", output_path)
    with open(output_path, 'w') as f:
        json.dump(substituted_actions, f, indent=2)
    
    logger.success("Token substitution completed successfully!")
    logger.statistics({
        "Output file": str(output_path),
        "Actions ready for execution": len(substituted_actions)
    })
    
    # Save execution summary
    summary_data = {
        "template_actions_file": str(template_path),
        "values_file": str(values_path),
        "output_file": str(output_path),
        "actions_processed": len(template_actions),
        "tokens_found": len(tokens_found),
        "tokens_substituted": len(tokens_substituted),
        "total_substitutions": total_substitutions,
        "success": True
    }
    logger.save_execution_summary(summary_data)
    
    return 0


if __name__ == "__main__":
    exit(main())
