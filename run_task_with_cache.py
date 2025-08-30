#!/usr/bin/env python3
"""
Enhanced run_task.py that enables LLM caching before running tasks.

This script wraps the existing run_task.py functionality but enables caching
so that repeated runs of identical tasks will use cached LLM responses.
"""

import asyncio
import sys
import time
from pathlib import Path

# Enable caching before any BrowserUse imports
import browser_use_cache_patch
browser_use_cache_patch.enable_cache()

# Now import the existing run_task functionality
sys.path.append(str(Path(__file__).parent / "browser_use" / "cache" / "prompt"))
from run_task import main as run_task_main


async def main():
	print("🎯 BrowserUse with LLM Caching Enabled")
	print("="*50)
	
	# Show current cache stats
	print("\n📊 Current cache stats:")
	browser_use_cache_patch.cache_stats()
	
	print("\n🚀 Running task...")
	start_time = time.time()
	
	try:
		# Run the original task
		await run_task_main()
		
		elapsed_time = time.time() - start_time
		print(f"\n✅ Task completed in {elapsed_time:.2f} seconds")
		
		# Show updated cache stats
		print("\n📊 Updated cache stats:")
		browser_use_cache_patch.cache_stats()
		
	except Exception as e:
		elapsed_time = time.time() - start_time
		print(f"\n❌ Task failed after {elapsed_time:.2f} seconds: {e}")
		raise


if __name__ == "__main__":
	asyncio.run(main())