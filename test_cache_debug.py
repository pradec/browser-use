#!/usr/bin/env python3
"""
Test cache with debugging to see exactly what's different between requests.
"""

import asyncio
import os
import sys
from pathlib import Path

# Set up environment and debugging
sys.path.insert(0, str(Path(__file__).parent))
os.environ['BROWSER_USE_LLM_CACHE'] = 'true'

# Import and enable debugging
from debug_cache_keys import debug_cache_key_generation
debug_generate_key = debug_cache_key_generation()

# Import cache components
from browser_use.cache.llm.cached_logger_wrapper import CachedLLMLoggerWrapper
from browser_use.llm import UserMessage, SystemMessage


class MockLLM:
    def __init__(self, model="gpt-4.1-mini"):
        self.model = model
        self.model_name = model
        self.call_count = 0
    
    async def ainvoke(self, messages, output_format=None):
        self.call_count += 1
        print(f"\n🔄 MOCK API CALL #{self.call_count}")
        
        class MockResult:
            def __init__(self):
                self.completion = {"action": "test", "response": f"Response {mock_llm.call_count}"}
                self.usage = {
                    "prompt_tokens": 100,
                    "prompt_cached_tokens": 0,
                    "prompt_cache_creation_tokens": None,
                    "prompt_image_tokens": None,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
        
        return MockResult()


async def test_with_browser_like_content():
    """Test with content similar to actual BrowserUse requests."""
    print("🧪 Testing with browser-like content")
    print("=" * 50)
    
    global mock_llm
    mock_llm = MockLLM()
    log_dir = Path.cwd() / "debug_logs"
    cached_llm = CachedLLMLoggerWrapper(mock_llm, lambda: log_dir)
    
    # Create system message (will be skipped in cache key)
    system_msg = SystemMessage(content="You are a browser automation agent. [LARGE SYSTEM PROMPT]")
    
    # Create user message with multi-part content like BrowserUse
    user_msg1 = UserMessage(content=[
        {
            "type": "text",
            "text": f"""<agent_history>
<sys>Agent initialized</sys>
</agent_history>

<agent_state>
<user_request>Login to example.com</user_request>
<step_info>
Step 1 of 100 max possible steps
Current date and time: 2025-08-19 22:47
</step_info>
</agent_state>

<browser_state>
Current tab: 4FA9
Page info: 1200x909px viewport
Interactive elements:
[1]<input type=text placeholder=Enter username />
[2]<input type=password placeholder=Enter password />
[3]<button>Sign In</button>
</browser_state>"""
        },
        {
            "type": "text", 
            "text": "Current screenshot:"
        }
    ])
    
    # Similar message with different timestamp and tab ID
    user_msg2 = UserMessage(content=[
        {
            "type": "text",
            "text": f"""<agent_history>
<sys>Agent initialized</sys>
</agent_history>

<agent_state>
<user_request>Login to example.com</user_request>
<step_info>
Step 1 of 100 max possible steps
Current date and time: 2025-08-20 10:30
</step_info>
</agent_state>

<browser_state>
Current tab: 5GB2
Page info: 1200x909px viewport
Interactive elements:
[1]<input type=text placeholder=Enter username />
[2]<input type=password placeholder=Enter password />
[3]<button>Sign In</button>
</browser_state>"""
        },
        {
            "type": "text",
            "text": "Current screenshot:"
        }
    ])
    
    messages1 = [system_msg, user_msg1]
    messages2 = [system_msg, user_msg2]
    
    print("\n🔍 FIRST REQUEST:")
    result1 = await cached_llm.ainvoke(messages1)
    
    print("\n🔍 SECOND REQUEST (should be similar):")
    result2 = await cached_llm.ainvoke(messages2)
    
    print(f"\n📊 SUMMARY:")
    print(f"API calls made: {mock_llm.call_count}")
    if mock_llm.call_count == 1:
        print("🎉 Cache hit! Second request used cached response.")
    else:
        print("❌ Cache miss. Different cache keys generated.")


if __name__ == "__main__":
    asyncio.run(test_with_browser_like_content())