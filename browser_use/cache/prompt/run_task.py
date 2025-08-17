import asyncio
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.browser import BrowserProfile


load_dotenv()

# Enable LLM call logging
os.environ["BROWSER_USE_LLM_CALL_LOGS"] = "true"


def load_task_prompt(prompt_input: str) -> str:
    """Load task prompt from either direct input or file."""
    # Check if it's a file path
    if os.path.isfile(prompt_input):
        try:
            with open(prompt_input, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                print(f"📄 Loaded task prompt from file: {prompt_input}")
                return content
        except Exception as e:
            raise RuntimeError(f"Failed to read prompt file '{prompt_input}': {e}")
    else:
        # Treat as direct prompt text
        print("📝 Using direct prompt input")
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

    args = parser.parse_args()

    # Ensure API key is present
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set. Add it to your environment or .env file.")

    # Load task prompt
    task_prompt = load_task_prompt(args.prompt)
    
    # Use specified model or environment override
    model_name = os.getenv("OPENAI_MODEL", args.model)
    base_llm = ChatOpenAI(model=model_name)
    print(f"🤖 Using model: {model_name}")

    # Set up browser profile
    profile_kwargs = {
        "headless": args.headless,
        "wait_between_actions": args.wait,
    }
    
    # Add allowed domains if specified
    if args.domain:
        profile_kwargs["allowed_domains"] = args.domain
        print(f"🌐 Allowed domains: {args.domain}")
    else:
        print("🌐 No domain restrictions (allowing all domains)")

    profile = BrowserProfile(**profile_kwargs)

    # Create and run agent
    agent = Agent(
        task=task_prompt,
        llm=base_llm,
        browser_profile=profile,
    )

    print(f"🚀 Starting task execution...")
    print(f"📋 Task: {task_prompt[:100]}{'...' if len(task_prompt) > 100 else ''}")
    
    # LLM logging is controlled via BROWSER_USE_LLM_CALL_LOGS=true
    # Logs will be written to <agent_dir>/llm_calls/
    
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
