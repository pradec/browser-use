import asyncio
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.browser import BrowserProfile
from task_logger import get_logger


load_dotenv()

# Enable LLM call logging
os.environ["BROWSER_USE_LLM_CALL_LOGS"] = "true"

# Configure clickable element detection
os.environ["CLICKABLE_ELEMENT_ICON_CLASS"] = "false"
os.environ["CLICKABLE_ELEMENT_TAG_LABEL"] = "false"


def load_task_prompt(prompt_input: str, logger) -> str:
    """Load task prompt from either direct input or file."""
    # Check if it's a file path
    if os.path.isfile(prompt_input):
        try:
            with open(prompt_input, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.file_operation("loaded task prompt from file", Path(prompt_input))
                return content
        except Exception as e:
            logger.error(f"Failed to read prompt file '{prompt_input}': {e}")
            raise RuntimeError(f"Failed to read prompt file '{prompt_input}': {e}")
    else:
        # Treat as direct prompt text
        logger.info("📝 Using direct prompt input")
        return prompt_input.strip()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic browser automation task runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using a prompt file
  python run_task.py --prompt preauth_request.md
  
  # Using direct prompt text
  python run_task.py --prompt "Navigate to example.com and click the login button"
  
  # With custom model and domains
  python run_task.py --prompt task.md --model gpt-4o --domain "example.com" --domain "*.example.org"
        """
    )
    
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Task prompt (either direct text or path to file containing prompt)"
    )
    
    parser.add_argument(
        "--model", "-m",
        default="gpt-4.1-mini",
        help="OpenAI model to use (default: gpt-4.1-mini)"
    )
    
    parser.add_argument(
        "--domain", "-d",
        action="append",
        help="Allowed domain(s) for browser profile (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: visible browser)"
    )
    
    parser.add_argument(
        "--wait",
        type=float,
        default=0.5,
        help="Wait time between actions in seconds (default: 0.5)"
    )

    parser.add_argument(
        "--run-dir",
        help="Run directory for logging (optional)"
    )

    args = parser.parse_args()

    # Initialize logger
    if args.run_dir:
        run_dir = Path(args.run_dir)
        logger = get_logger("run_task", run_dir)
    else:
        logger = get_logger("run_task")

    # Ensure API key is present
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not set. Add it to your environment or .env file.")
        raise RuntimeError("OPENAI_API_KEY not set. Add it to your environment or .env file.")

    # Load task prompt
    task_prompt = load_task_prompt(args.prompt, logger)
    
    # Use specified model or environment override
    model_name = os.getenv("OPENAI_MODEL", args.model)
    base_llm = ChatOpenAI(model=model_name)
    logger.info(f"🤖 Using model: {model_name}")

    # Set up browser profile
    profile_kwargs = {
        "headless": args.headless,
        "wait_between_actions": args.wait,
    }
    
    # Add allowed domains if specified
    if args.domain:
        profile_kwargs["allowed_domains"] = args.domain
        logger.info(f"🌐 Allowed domains: {args.domain}")
    else:
        logger.info("🌐 No domain restrictions (allowing all domains)")

    profile = BrowserProfile(**profile_kwargs)

    # Create and run agent
    agent = Agent(
        task=task_prompt,
        llm=base_llm,
        browser_profile=profile,
    )

    logger.info(f"🚀 Starting task execution...")
    task_preview = task_prompt[:100] + '...' if len(task_prompt) > 100 else task_prompt
    logger.info(f"📋 Task: {task_preview}")
    
    # LLM logging is controlled via BROWSER_USE_LLM_CALL_LOGS=true
    # Logs will be written to <agent_dir>/llm_calls/
    
    try:
        result = await agent.run()
        
        logger.success("Task execution completed")
        
        # Save execution summary
        summary_data = {
            "prompt_file": args.prompt,
            "model": model_name,
            "headless": args.headless,
            "wait_time": args.wait,
            "domains": args.domain,
            "task_preview": task_preview,
            "success": True
        }
        logger.save_execution_summary(summary_data)
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        
        summary_data = {
            "prompt_file": args.prompt,
            "model": model_name,
            "headless": args.headless,
            "wait_time": args.wait,
            "domains": args.domain,
            "task_preview": task_preview,
            "success": False,
            "error": str(e)
        }
        logger.save_execution_summary(summary_data)
        raise


if __name__ == "__main__":
    asyncio.run(main())
