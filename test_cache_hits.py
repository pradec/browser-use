#!/usr/bin/env python3
"""
Test cache hits and misses by running identical requests
"""

import asyncio
import os
import sys
from pathlib import Path

# Add to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Enable caching
os.environ['BROWSER_USE_LLM_CACHE'] = 'true'

from browser_use.cache.llm.cached_logger_wrapper import CachedLLMLoggerWrapper
from browser_use.llm import UserMessage, SystemMessage
from browser_use.llm.views import ChatInvokeCompletion


class MockLLM:
	def __init__(self, model="gpt-4.1-mini"):
		self.model = model
		self.model_name = model
		self.call_count = 0
	
	async def ainvoke(self, messages, output_format=None):
		self.call_count += 1
		print(f"🔄 ACTUAL API CALL #{self.call_count}")
		await asyncio.sleep(0.1)  # Simulate API delay
		
		class MockResult:
			def __init__(self):
				self.completion = {"action": "test", "response": f"Call #{mock_llm.call_count}"}
				self.usage = {
					"prompt_tokens": 100,
					"prompt_cached_tokens": 0,
					"prompt_cache_creation_tokens": None,
					"prompt_image_tokens": None,
					"completion_tokens": 50,
					"total_tokens": 150
				}
		
		return MockResult()


async def test_cache_hits_and_misses():
	print("🧪 Testing Cache Hits vs Misses")
	print("=" * 40)
	
	# Create mock LLM and wrap with cache
	global mock_llm
	mock_llm = MockLLM()
	log_dir = Path.cwd() / "cache_test_logs"
	cached_llm = CachedLLMLoggerWrapper(mock_llm, lambda: log_dir)
	
	# Test messages - these should be identical after masking
	system_msg = SystemMessage(content="You are a test agent.")
	
	# Message 1: Will be cached
	user_msg1 = UserMessage(content="""
	<step_info>
	Step 1 of 10 max possible steps
	Current date and time: 2025-08-19 22:47
	</step_info>
	
	Navigate to example.com
	""")
	
	# Message 2: Identical content after masking
	user_msg2 = UserMessage(content="""
	<step_info>
	Step 1 of 10 max possible steps
	Current date and time: 2025-08-20 10:30
	</step_info>
	
	Navigate to example.com
	""")
	
	# Message 3: Different content
	user_msg3 = UserMessage(content="""
	<step_info>
	Step 2 of 10 max possible steps
	Current date and time: 2025-08-20 10:30
	</step_info>
	
	Navigate to google.com
	""")
	
	messages1 = [system_msg, user_msg1]
	messages2 = [system_msg, user_msg2]  # Should hit cache (same after masking)
	messages3 = [system_msg, user_msg3]  # Should miss cache (different content)
	
	print("📞 Call 1: Original request")
	result1 = await cached_llm.ainvoke(messages1)
	print(f"   API calls so far: {mock_llm.call_count}")
	
	print("\n📞 Call 2: Same request with different timestamp (should hit cache)")
	result2 = await cached_llm.ainvoke(messages2)
	print(f"   API calls so far: {mock_llm.call_count}")
	
	print("\n📞 Call 3: Different request (should miss cache)")
	result3 = await cached_llm.ainvoke(messages3)
	print(f"   API calls so far: {mock_llm.call_count}")
	
	print("\n📞 Call 4: Repeat of call 1 (should hit cache)")
	result4 = await cached_llm.ainvoke(messages1)
	print(f"   API calls so far: {mock_llm.call_count}")
	
	print(f"\n📊 SUMMARY:")
	print(f"   Total requests made: 4")
	print(f"   Actual API calls: {mock_llm.call_count}")
	print(f"   Cache hits: {4 - mock_llm.call_count}")
	print(f"   Cache misses: {mock_llm.call_count}")
	
	if mock_llm.call_count <= 2:
		print("🎉 Cache is working effectively!")
	else:
		print("⚠️  Cache may not be working as expected")


if __name__ == "__main__":
	asyncio.run(test_cache_hits_and_misses())