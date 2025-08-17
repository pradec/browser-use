#!/usr/bin/env python3
"""
Enhanced JSON action runner for Browser Use with comprehensive screenshot capture and failure logging.

This script loads actions from a JSON file and executes them step by step while:
- Capturing screenshots before and after each action
- Logging detailed execution information
- Creating agent directories like Browser Use agent
- Providing comprehensive failure analysis
"""

import argparse
import asyncio
import base64
import json
import tempfile
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from browser_use import Controller
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.filesystem.file_system import FileSystem


class ActionExecutionLogger:
    """Enhanced logging and screenshot capture for action execution."""
    
    def __init__(self, agent_directory: Path):
        self.agent_directory = agent_directory
        self.agent_directory.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories like Browser Use agent
        self.screenshots_dir = self.agent_directory / "screenshots"
        self.logs_dir = self.agent_directory / "logs"
        self.screenshots_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Execution log
        self.execution_log = []
        self.screenshot_counter = 0
        
    async def capture_screenshot(self, browser_session: BrowserSession, label: str) -> Optional[str]:
        """Capture a screenshot and save it to disk."""
        try:
            # Get DOM state summary which includes screenshot
            dom_summary = await browser_session.get_browser_state_summary(include_screenshot=True)
            
            if dom_summary.screenshot:
                self.screenshot_counter += 1
                
                # Save with descriptive name
                descriptive_name = f"{self.screenshot_counter:03d}_{label}.png"
                descriptive_path = self.screenshots_dir / descriptive_name
                
                # Decode base64 and save screenshot
                screenshot_data = base64.b64decode(dom_summary.screenshot)
                with open(descriptive_path, 'wb') as f:
                    f.write(screenshot_data)
                
                print(f"📸 Screenshot saved: {descriptive_name}")
                return str(descriptive_path)
                
        except Exception as e:
            print(f"⚠️ Failed to capture screenshot '{label}': {e}")
            
        return None
    
    async def log_action_start(self, action_index: int, action: Dict[str, Any], browser_session: BrowserSession):
        """Log the start of an action with screenshot."""
        action_name = list(action.keys())[0] if action else "unknown"
        
        print(f"\n🎬 Starting Action {action_index + 1}: {action_name}")
        print(f"   Action details: {json.dumps(action, indent=2)}")
        
        # Capture before screenshot
        before_screenshot = await self.capture_screenshot(
            browser_session, f"action_{action_index + 1:02d}_before_{action_name}"
        )
        
        # Get DOM state summary
        dom_summary = await browser_session.get_browser_state_summary()
        
        log_entry = {
            "action_index": action_index + 1,
            "action_name": action_name,
            "action_details": action,
            "timestamp_start": datetime.now().isoformat(),
            "before_screenshot": before_screenshot,
            "dom_state_available": dom_summary is not None,
            "page_url": dom_summary.url if dom_summary else None,
            "page_title": dom_summary.title if dom_summary else None,
        }
        
        self.execution_log.append(log_entry)
        return len(self.execution_log) - 1  # Return index for later updating
    
    async def log_action_result(self, log_index: int, success: bool, error_msg: Optional[str], browser_session: BrowserSession):
        """Log the result of an action with screenshot."""
        if log_index >= len(self.execution_log):
            return
            
        log_entry = self.execution_log[log_index]
        action_name = log_entry["action_name"]
        action_index = log_entry["action_index"]
        
        # Capture after screenshot
        after_screenshot = await self.capture_screenshot(
            browser_session, f"action_{action_index:02d}_after_{action_name}{'_SUCCESS' if success else '_FAILED'}"
        )
        
        # Get updated DOM state
        dom_summary = await browser_session.get_browser_state_summary()
        
        # Update log entry
        log_entry.update({
            "timestamp_end": datetime.now().isoformat(),
            "success": success,
            "error_message": error_msg,
            "after_screenshot": after_screenshot,
            "dom_state_available_after": dom_summary is not None,
            "page_url_after": dom_summary.url if dom_summary else None,
        })
        
        if success:
            print(f"✅ Action {action_index} completed successfully")
        else:
            print(f"❌ Action {action_index} failed: {error_msg}")
            
            # For failures, also capture detailed DOM state
            if dom_summary and dom_summary.dom_state:
                dom_dump_path = self.logs_dir / f"action_{action_index:02d}_dom_failure.json"
                with open(dom_dump_path, 'w') as f:
                    json.dump({
                        "dom_representation": dom_summary.dom_state.llm_representation(),
                        "page_url": dom_summary.url,
                        "page_title": dom_summary.title,
                        "error_context": error_msg
                    }, f, indent=2)
                print(f"🔍 DOM state saved for debugging: {dom_dump_path}")
    
    def save_execution_summary(self):
        """Save comprehensive execution summary."""
        summary_path = self.logs_dir / "execution_summary.json"
        
        # Calculate statistics
        total_actions = len(self.execution_log)
        successful_actions = sum(1 for log in self.execution_log if log.get("success", False))
        failed_actions = total_actions - successful_actions
        success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
        
        summary = {
            "execution_timestamp": datetime.now().isoformat(),
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "success_rate_percent": round(success_rate, 2),
            "detailed_log": self.execution_log,
            "screenshots_captured": self.screenshot_counter,
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 Execution Summary:")
        print(f"   Total Actions: {total_actions}")
        print(f"   Successful: {successful_actions}")
        print(f"   Failed: {failed_actions}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Screenshots Captured: {self.screenshot_counter}")
        print(f"   Summary saved to: {summary_path}")
        
        # Print failure analysis
        if failed_actions > 0:
            print(f"\n🔍 Failed Actions Analysis:")
            for log in self.execution_log:
                if not log.get("success", False):
                    print(f"   Action {log['action_index']}: {log['action_name']} - {log.get('error_message', 'Unknown error')}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced JSON action runner with screenshots and detailed logging")
    parser.add_argument("json_file", help="Path to JSON file containing actions")
    parser.add_argument("--url", default="https://mellow-belekoy-b56ebb.netlify.app/", help="URL to navigate to")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue execution on action errors")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between actions in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()


def create_agent_directory() -> Path:
    """Create agent directory like Browser Use agent does."""
    timestamp = int(datetime.now().timestamp())
    # Generate a unique ID (simplified version)
    agent_id = str(uuid.uuid4())[:8]
    
    base_tmp = Path(tempfile.gettempdir())
    agent_directory = base_tmp / f'browser_use_agent_{agent_id}_{timestamp}'
    return agent_directory


async def execute_actions_with_logging(
    actions: List[Dict[str, Any]], 
    controller: Controller, 
    browser_session: BrowserSession,
    file_system: FileSystem,
    logger: ActionExecutionLogger,
    continue_on_error: bool = True,
    delay: float = 1.0,
    verbose: bool = False
) -> None:
    """Execute actions with comprehensive logging and screenshot capture."""
    
    print(f"🚀 Starting execution of {len(actions)} actions with enhanced logging...")
    
    # Capture initial state
    await logger.capture_screenshot(browser_session, "initial_state")
    
    # Create ActionModel from the controller registry
    ActionModel = controller.registry.create_action_model()
    
    for i, action in enumerate(actions):
        try:
            # Log action start with before screenshot
            log_index = await logger.log_action_start(i, action, browser_session)
            
            # Convert action dict to ActionModel
            action_model = ActionModel.model_validate(action)
            
            # Execute the action
            result = await controller.act(
                action=action_model,
                browser_session=browser_session,
                file_system=file_system,
            )
            
            if result.error:
                raise Exception(result.error)
            
            # Log successful completion
            await logger.log_action_result(log_index, True, None, browser_session)
            
        except Exception as e:
            error_msg = str(e)
            
            # Log failure with detailed context
            if 'log_index' in locals():
                await logger.log_action_result(log_index, False, error_msg, browser_session)
            
            # Check if this is an expected error that we can skip
            expected_errors = [
                "requires page_extraction_llm but none provided",
                "Element index", "not found in DOM"
            ]
            
            is_expected = any(expected in error_msg for expected in expected_errors)
            
            if not continue_on_error and not is_expected:
                print(f"🛑 Stopping execution due to error in action {i + 1}")
                break
            elif is_expected and verbose:
                print(f"   ⚠️ Skipping expected error for action {i + 1}")
        
        # Optional delay between actions
        if i < len(actions) - 1 and delay > 0:
            await asyncio.sleep(delay)
    
    # Capture final state
    await logger.capture_screenshot(browser_session, "final_state")


async def main():
    """Main execution function."""
    load_dotenv()
    args = parse_args()
    
    # Create agent directory like Browser Use agent does
    agent_directory = create_agent_directory()
    print(f"📁 Agent directory: {agent_directory}")
    
    # Initialize logger
    logger = ActionExecutionLogger(agent_directory)
    
    # Load actions from JSON file
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return 1
    
    with open(json_path, 'r') as f:
        actions = json.load(f)
    
    if not isinstance(actions, list):
        print("❌ JSON file must contain a list of actions")
        return 1
    
    print(f"📋 Loaded {len(actions)} actions from {json_path}")
    
    # Set up browser profile - use original website
    profile = BrowserProfile(
        headless=args.headless,
        wait_between_actions=args.delay,
    )
    
    # Create controller and file system
    controller = Controller()
    file_system = FileSystem(base_dir=str(agent_directory), create_default_files=True)
    
    # Create browser session
    browser_session = BrowserSession(browser_profile=profile)
    
    try:
        # Start browser session
        await browser_session.start()
        
        # Create ActionModel from the controller registry
        ActionModel = controller.registry.create_action_model()
        
        # Navigate to the target URL using controller
        if args.url:
            print(f"🌐 Navigating to: {args.url}")
            go_to_url_action = ActionModel.model_validate({
                "go_to_url": {"url": args.url}
            })
            
            result = await controller.act(
                action=go_to_url_action,
                browser_session=browser_session,
                file_system=file_system,
            )
            
            if result.error:
                print(f"❌ Failed to navigate to {args.url}: {result.error}")
                return 1
            
            # Wait for page to load
            await asyncio.sleep(3)
        
        # Execute actions with logging
        await execute_actions_with_logging(
            actions=actions,
            controller=controller,
            browser_session=browser_session,
            file_system=file_system,
            logger=logger,
            continue_on_error=args.continue_on_error,
            delay=args.delay,
            verbose=args.verbose
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Execution interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1
    finally:
        # Save execution summary
        logger.save_execution_summary()
        
        # Clean up browser session
        await browser_session.stop()
        
        print(f"\n🏁 Execution completed. Results saved to: {agent_directory}")
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))