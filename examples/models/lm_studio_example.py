"""
Example of using Browser Use with LM Studio local LLM.

Setup:
1. Start LM Studio and load your preferred model
2. Enable the local server (usually http://localhost:1234)
3. Run this script

No API key needed for local models!
"""

import asyncio
from browser_use import Agent
from browser_use.llm import ChatOpenAI

# Configure Browser Use to use LM Studio local server
llm = ChatOpenAI(
    model="local-model",  # This can be any string since LM Studio ignores it
    base_url="http://localhost:1234/v1",  # LM Studio's OpenAI-compatible endpoint
    api_key="lm-studio",  # LM Studio doesn't require a real API key, but we need to provide something
    temperature=0.1,
)

async def main():
    agent = Agent(
        task="Go to example.com and tell me what you see on the page",
        llm=llm,
    )
    
    result = await agent.run(max_steps=10)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
