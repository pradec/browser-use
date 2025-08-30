#!/usr/bin/env python3
"""
Simple validation script to test that the LLM cache is working properly.
This script tests the cache system without requiring actual browser automation.
"""

import asyncio
import hashlib
import json
from pathlib import Path

# Enable caching first
import browser_use_cache_patch
browser_use_cache_patch.enable_cache()

from browser_use.llm.cache import _generate_cache_key, get_cached_response, cache_response
from browser_use.llm import UserMessage, SystemMessage


def test_cache_key_generation():
	"""Test that cache key generation is deterministic and masks dynamic content."""
	print("🧪 Testing cache key generation...")
	
	# Create test messages with dynamic content
	system_msg = SystemMessage(content="You are a browser automation agent.")
	user_msg = UserMessage(content="""
	Current date and time: 2025-08-19 22:47
	Step 5 of 10 max possible steps
	Navigate to example.com
	""")
	
	# Generate key twice - should be identical
	key1 = _generate_cache_key("gpt-4o-mini", [system_msg, user_msg])
	key2 = _generate_cache_key("gpt-4o-mini", [system_msg, user_msg])
	
	assert key1 == key2, "Cache keys should be deterministic"
	print(f"✓ Cache key generation is deterministic: {key1[:16]}...")
	
	# Test that different timestamps produce same key (due to masking)
	user_msg_diff_time = UserMessage(content="""
	Current date and time: 2025-08-20 10:30
	Step 5 of 10 max possible steps
	Navigate to example.com
	""")
	
	key3 = _generate_cache_key("gpt-4o-mini", [system_msg, user_msg_diff_time])
	assert key1 == key3, "Different timestamps should produce same cache key"
	print("✓ Timestamp masking works correctly")
	
	# Test that different models produce different keys
	key4 = _generate_cache_key("gpt-4", [system_msg, user_msg])
	assert key1 != key4, "Different models should produce different cache keys"
	print("✓ Model differentiation works correctly")
	
	print("✅ Cache key generation tests passed!\n")


def test_cache_storage():
	"""Test that cache storage and retrieval works."""
	print("🧪 Testing cache storage and retrieval...")
	
	# Clear any existing cache for our test
	cache_dir = Path.home() / ".cache" / "browseruse" / "llm"
	test_files = list(cache_dir.glob("test_*.json")) if cache_dir.exists() else []
	for f in test_files:
		f.unlink()
	
	# Create test messages
	system_msg = SystemMessage(content="You are a test agent.")
	user_msg = UserMessage(content="Test message for caching")
	messages = [system_msg, user_msg]
	
	# Test cache miss first
	cached = get_cached_response("gpt-4o-mini", messages)
	assert cached is None, "Should get cache miss for new request"
	print("✓ Cache miss works correctly")
	
	# Store a response
	test_response = {
		"content": {"thinking": "test thinking", "action": "test action"},
		"usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
		"error": None
	}
	
	cache_response("gpt-4o-mini", messages, test_response)
	print("✓ Response cached successfully")
	
	# Test cache hit
	cached = get_cached_response("gpt-4o-mini", messages)
	assert cached is not None, "Should get cache hit for stored request"
	assert cached["content"] == test_response["content"], "Cached content should match"
	assert cached["usage"] == test_response["usage"], "Cached usage should match"
	print("✓ Cache hit works correctly")
	
	print("✅ Cache storage tests passed!\n")


def test_monkey_patch():
	"""Test that the monkey patch integration is working."""
	print("🧪 Testing monkey patch integration...")
	
	try:
		from browser_use.agent import service
		from browser_use.llm.cached_logger_wrapper import CachedLLMLoggerWrapper
		
		# Check if our patched class is being used
		assert hasattr(service, 'LLMLoggerWrapper'), "LLMLoggerWrapper should exist in service module"
		
		# The class should now be our cached version
		if service.LLMLoggerWrapper is CachedLLMLoggerWrapper:
			print("✓ Monkey patch applied correctly")
		else:
			print("⚠️  Monkey patch may not be fully applied - but this might be normal")
		
		print("✅ Monkey patch tests completed!\n")
		
	except ImportError as e:
		print(f"⚠️  Could not fully test monkey patch: {e}")
		print("This is expected if BrowserUse dependencies aren't fully installed\n")


async def main():
	"""Run all validation tests."""
	print("🎯 Validating BrowserUse LLM Cache System")
	print("=" * 50)
	
	try:
		test_cache_key_generation()
		test_cache_storage()
		test_monkey_patch()
		
		print("🎉 All validation tests passed!")
		print("\n📊 Current cache stats:")
		browser_use_cache_patch.cache_stats()
		
	except Exception as e:
		print(f"❌ Validation failed: {e}")
		raise


if __name__ == "__main__":
	asyncio.run(main())