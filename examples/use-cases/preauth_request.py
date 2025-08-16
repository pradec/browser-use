import asyncio
import os
from dotenv import load_dotenv

from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.browser import BrowserProfile
from pathlib import Path


load_dotenv()


TASK_PROMPT = (
    """
Login in https://mellow-belekoy-b56ebb.netlify.app using "demo" as user name and "demo" as password. Post that submit a preauthorization request for a patient with the following details.

Name: Anurag Sinha
Date of Birth: "01/07/2001"
Member Id: 12345
Group Number: 12
Phone Number: 9991123322
Email: abc@def.com
Service Type: MRI
CPT Code: 72188
Diagnosis: Persistent pain
Critical Justification: Required to rule out
Urgency: Routine
Requested Date: "01/01/2025"
"""
).strip()


async def main() -> None:
    # Ensure API key is present
    if not (os.getenv("OPENAI_API_KEY")):
        raise RuntimeError("OPENAI_API_KEY not set. Add it to your environment or .env file.")

    # Use OpenAI's gpt-5-mini
    base_llm = ChatOpenAI(model="gpt-5-mini")

    # Constrain the agent to the target app domain for safety
    profile = BrowserProfile(
        allowed_domains=[
            "mellow-belekoy-b56ebb.netlify.app",
            "*.netlify.app",
        ],
        # Set headless to False if you want to watch the actions
        # headless=False,
        wait_between_actions=0.5,
    )

    agent = Agent(
        task=TASK_PROMPT,
        llm=base_llm,
        browser_profile=profile,
    )

    # LLM logging is now controlled via config: set BROWSER_USE_LLM_CALL_LOGS=true
    # Logs will be written to <agent_dir>/<BROWSER_USE_LLM_LOGS_DIRNAME>

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
