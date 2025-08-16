#!/usr/bin/env python3
"""
Simple JSON action runner for Browser Use.

Loads actions from a JSON file and executes them directly using Controller.
No LLM calls are made - just direct action execution.
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from browser_use import Controller
from browser_use.browser import BrowserProfile, BrowserSession


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Browser Use actions from a JSON file")
    
    parser.add_argument(
        "--json-file",
        type=str,
        required=True,
        help="Path to JSON file containing actions to execute"
    )
    
    parser.add_argument(
        "--start-url", 
        type=str,
        default="https://mellow-belekoy-b56ebb.netlify.app/",
        help="Starting URL for the browser (default: https://mellow-belekoy-b56ebb.netlify.app/)"
    )
    
    parser.add_argument(
        "--allowed-domains",
        type=str,
        nargs="+",
        help="List of allowed domains for the browser"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between actions in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue executing actions even if one fails"
    )
    
    parser.add_argument(
        "--agent-dir",
        type=str,
        help="Agent directory to use for file system (where logs/screenshots are stored)"
    )
    
    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()
    
    # Load actions from JSON file
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}")
        return 1
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            actions = json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return 1
    
    if not isinstance(actions, list):
        print("Error: JSON file must contain a list of actions")
        return 1
    
    print(f"Loaded {len(actions)} actions from {json_path}")
    
    # Set up browser profile
    profile = BrowserProfile(
        allowed_domains=args.allowed_domains or ["https://mellow-belekoy-b56ebb.netlify.app"],
        headless=False,
        wait_between_actions=args.delay,
    )
    
    async def run_actions():
        # Create controller and browser session
        controller = Controller()
        
        # Create file system for file operations
        from browser_use.filesystem.file_system import FileSystem
        
        # Use agent directory if provided, otherwise default to ./browser_use_output
        base_dir = args.agent_dir if args.agent_dir else "./browser_use_output"
        if args.verbose:
            print(f"📁 Using FileSystem base directory: {base_dir}")
        
        file_system = FileSystem(base_dir=base_dir, create_default_files=True)
        
        # Create browser session
        browser_session = BrowserSession(
            browser_profile=profile,
        )
        
        # Start the browser session
        await browser_session.start()
        
        # Create ActionModel from the controller registry
        ActionModel = controller.registry.create_action_model()
        
        # Navigate to start URL and wait for page to load
        if args.start_url:
            if args.verbose:
                print(f"🌐 Navigating to {args.start_url}...")
            
            # Use controller to navigate to start URL
            go_to_url_action = ActionModel.model_validate({
                "go_to_url": {"url": args.start_url}
            })
            
            result = await controller.act(
                action=go_to_url_action,
                browser_session=browser_session,
                file_system=file_system,
            )
            
            if result.error:
                print(f"❌ Failed to navigate to {args.start_url}: {result.error}")
                return
            
            # Wait a bit for page to load
            import asyncio
            await asyncio.sleep(5)  # Increased wait time for page to fully load
            
            if args.verbose:
                print("✅ Navigation completed")
                
            # CRITICAL: Trigger DOM indexing by getting browser state
            # This builds the element index mapping that actions need
            if args.verbose:
                print("🔍 Building DOM element indexes...")
            browser_state = await browser_session.get_browser_state_summary()
            
            if args.verbose:
                element_count = len(browser_state.dom_state.selector_map) if browser_state.dom_state else 0
                print(f"✅ DOM indexing completed - found {element_count} interactive elements")

        try:
            if args.verbose:
                print(f"Starting action execution with {len(actions)} actions...")
            
            # Execute all actions using controller
            for i, action_dict in enumerate(actions, 1):
                if args.verbose:
                    action_name = next(iter(action_dict.keys())) if action_dict else 'unknown'
                    print(f"🦾 [ACTION {i}/{len(actions)}] {action_name}...")
                
                # Create ActionModel from the transformed format
                try:
                    action_model = ActionModel.model_validate(action_dict)
                except Exception as e:
                    print(f"❌ Validation failed for action {i}: {e}")
                    raise
                
                # For actions that depend on DOM elements, refresh DOM state
                action_name = next(iter(action_dict.keys()))
                if action_name in ['input_text', 'click_element_by_index', 'scroll_element_by_index']:
                    if args.verbose:
                        print(f"🔄 Refreshing DOM state before {action_name}...")
                    # Refresh DOM indexing to ensure element indexes are current
                    await browser_session.get_browser_state_summary()
                
                result = await controller.act(
                    action=action_model,
                    browser_session=browser_session,
                    file_system=file_system,
                )
                
                if result.error:
                    error_msg = str(result.error)
                    print(f"❌ Action {i} failed: {error_msg}")
                    
                    # Check if this is an expected error that we can skip
                    expected_errors = [
                        "requires page_extraction_llm but none provided",  # extract_structured_data without LLM
                        "Element index", "not found in DOM"  # DOM element not found
                    ]
                    
                    is_expected = any(expected in error_msg for expected in expected_errors)
                    
                    if not args.continue_on_error and not is_expected:
                        break
                    elif is_expected and args.verbose:
                        print(f"   ⚠️ Skipping expected error for {action_name}")
                elif args.verbose:
                    print(f"✅ Action {i} completed")
                
                # Optional delay between actions
                if i < len(actions) and args.delay > 0:
                    await asyncio.sleep(args.delay)
            
            print("✅ Action execution completed")
            
        finally:
            # Clean up browser session
            await browser_session.stop()
    
    # Run the actions
    try:
        asyncio.run(run_actions())
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Execution interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
