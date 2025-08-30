"""
Test script to verify LLM caching works with BrowserUse
"""

import asyncio
import time

# Enable caching before importing browser_use
import browser_use_cache_patch
browser_use_cache_patch.enable_cache()

from browser_use import Agent
from browser_use.llm import ChatOpenAI


async def test_cache():
	"""Test that identical requests are cached and don't hit the LLM twice."""
	print("🧪 Testing BrowserUse LLM Cache...")
	
	# Create agent - this will trigger some initial LLM calls
	llm = ChatOpenAI(model="gpt-4o-mini")
	
	agent = Agent(
		task="Navigate to https://example.com and tell me the title",
		llm=llm,
		use_vision=False,  # Disable vision to reduce variability
		max_steps=2  # Limit steps for testing
	)
	
	print("\n🚀 Running task first time (will make LLM calls)...")
	start_time = time.time()
	try:
		result1 = await agent.run()
		first_run_time = time.time() - start_time
		print(f"✓ First run completed in {first_run_time:.2f} seconds")
	except Exception as e:
		print(f"First run failed: {e}")
		return
	
	# Show cache stats
	print("\n📊 Cache stats after first run:")
	browser_use_cache_patch.cache_stats()
	
	print("\n🔄 Running same task again (should use cache)...")
	# Create new agent with same configuration
	agent2 = Agent(
		task="Navigate to https://example.com and tell me the title", 
		llm=llm,
		use_vision=False,
		max_steps=2
	)
	
	start_time = time.time()
	try:
		result2 = await agent2.run()
		second_run_time = time.time() - start_time
		print(f"✓ Second run completed in {second_run_time:.2f} seconds")
		
		if second_run_time < first_run_time * 0.8:  # Expect significant speedup
			print(f"🎉 Cache working! Second run was {first_run_time/second_run_time:.1f}x faster")
		else:
			print("⚠️  Cache may not be working - no significant speedup detected")
			
	except Exception as e:
		print(f"Second run failed: {e}")
	
	print("\n📊 Final cache stats:")
	browser_use_cache_patch.cache_stats()


if __name__ == "__main__":
	asyncio.run(test_cache())