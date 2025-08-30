#!/usr/bin/env python3
"""
Demonstration of the LLM cache system working independently.
This shows caching behavior without requiring full BrowserUse dependencies.
"""

import asyncio
import time
from pathlib import Path

# Enable caching
import browser_use_cache_patch
browser_use_cache_patch.enable_cache()

from browser_use.llm.cache import get_cached_response, cache_response, _generate_cache_key
from browser_use.llm.cached_logger_wrapper import CachedLLMLoggerWrapper
from browser_use.llm import UserMessage, SystemMessage
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage


class MockLLM:
	"""Mock LLM that simulates API calls with delays"""
	
	def __init__(self, model="gpt-4o-mini"):
		self.model = model
		self.model_name = model
		self.provider = "mock"
		self.name = "MockLLM"
		self.call_count = 0
	
	async def ainvoke(self, messages, output_format=None):
		self.call_count += 1
		print(f"🔄 Mock LLM API call #{self.call_count} (simulating 2s delay)...")
		await asyncio.sleep(2)  # Simulate API delay
		
		# Create mock response - simple object to avoid pydantic issues
		class MockResult:
			def __init__(self):
				self.completion = {
					"thinking": "I need to navigate to the website",
					"action": "navigate_to_url", 
					"url": "https://example.com"
				}
				self.usage = {
					"prompt_tokens": 100,
					"prompt_cached_tokens": 0,
					"prompt_cache_creation_tokens": None,
					"prompt_image_tokens": None,
					"completion_tokens": 50,
					"total_tokens": 150
				}
		
		return MockResult()


async def demo_caching():
	"""Demonstrate cache working with mock LLM calls."""
	print("🎯 LLM Cache System Demo")
	print("=" * 40)
	
	# Create mock LLM and wrap it with caching
	mock_llm = MockLLM()
	log_dir = Path.cwd() / "demo_logs"
	cached_llm = CachedLLMLoggerWrapper(mock_llm, lambda: log_dir)
	
	# Create test messages that would normally come from BrowserUse
	system_msg = SystemMessage(content="You are a browser automation agent.")
	user_msg = UserMessage(content="""
	<agent_state>
	Current date and time: 2025-08-19 22:47
	Step 3 of 10 max possible steps
	</agent_state>
	
	Navigate to example.com and click the login button.
	""")
	
	messages = [system_msg, user_msg]
	
	print(f"📝 Test messages created")
	print(f"🔑 Cache key: {_generate_cache_key(mock_llm.model, messages)[:16]}...")
	
	# First call - should hit the mock API
	print(f"\n🚀 First call (should call mock API)...")
	start_time = time.time()
	result1 = await cached_llm.ainvoke(messages)
	first_call_time = time.time() - start_time
	print(f"✅ First call completed in {first_call_time:.2f}s")
	print(f"   Mock API call count: {mock_llm.call_count}")
	
	# Second call - should use cache
	print(f"\n🎯 Second call (should use cache)...")
	start_time = time.time()
	result2 = await cached_llm.ainvoke(messages)
	second_call_time = time.time() - start_time
	print(f"✅ Second call completed in {second_call_time:.2f}s")
	print(f"   Mock API call count: {mock_llm.call_count}")
	
	# Verify results are equivalent
	if (hasattr(result1, 'completion') and hasattr(result2, 'completion') and 
		result1.completion == result2.completion):
		print("✅ Results are identical!")
	
	# Show speedup
	if second_call_time < first_call_time * 0.1:  # Cache should be much faster
		speedup = first_call_time / second_call_time
		print(f"🚀 Cache speedup: {speedup:.1f}x faster!")
	else:
		print("⚠️  Expected more significant speedup from caching")
	
	# Test with slightly different message (should also hit cache due to masking)
	user_msg_diff_time = UserMessage(content="""
	<agent_state>
	Current date and time: 2025-08-20 10:30
	Step 3 of 10 max possible steps
	</agent_state>
	
	Navigate to example.com and click the login button.
	""")
	
	messages_diff = [system_msg, user_msg_diff_time]
	
	print(f"\n🔄 Third call with different timestamp (should still use cache)...")
	start_time = time.time()
	result3 = await cached_llm.ainvoke(messages_diff)
	third_call_time = time.time() - start_time
	print(f"✅ Third call completed in {third_call_time:.2f}s")
	print(f"   Mock API call count: {mock_llm.call_count}")
	
	if mock_llm.call_count == 1:
		print("🎉 Perfect! Only one actual API call made despite 3 requests!")
	else:
		print(f"⚠️  Expected only 1 API call, but got {mock_llm.call_count}")
	
	print(f"\n📊 Final cache stats:")
	browser_use_cache_patch.cache_stats()


if __name__ == "__main__":
	asyncio.run(demo_caching())