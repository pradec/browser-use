"""
BrowserUse LLM Cache Patch

This module provides a monkey-patch mechanism to enable LLM response caching
for BrowserUse without modifying the core codebase.

Usage:
    import browser_use_cache_patch
    browser_use_cache_patch.enable_cache()
    
    # Now use BrowserUse normally - responses will be cached automatically
    from browser_use import Agent
    agent = Agent(...)
"""

import os
from pathlib import Path


def enable_cache():
	"""Enable LLM response caching for BrowserUse by monkey-patching the logger wrapper."""
	
	# Set environment variable to ensure logging is enabled
	# (the cache piggybacks on the logging infrastructure)
	os.environ['BROWSER_USE_LLM_CALL_LOGS'] = 'true'
	
	# Import and patch the agent service module
	try:
		from browser_use.llm.cached_logger_wrapper import CachedLLMLoggerWrapper
		
		# Try to patch the agent service module  
		try:
			from browser_use.agent import service
			
			# Store original class reference
			if not hasattr(service, '_original_LLMLoggerWrapper'):
				try:
					from browser_use.llm.logger_wrapper import LLMLoggerWrapper
					service._original_LLMLoggerWrapper = LLMLoggerWrapper
				except ImportError:
					service._original_LLMLoggerWrapper = None
			
			# Monkey patch the import in the service module
			service.LLMLoggerWrapper = CachedLLMLoggerWrapper
		except ImportError:
			print("⚠️  Could not patch agent.service module (this is expected during development)")
		
		# Also patch the logger_wrapper module itself in case other code imports it directly
		try:
			from browser_use.llm import logger_wrapper
			logger_wrapper.LLMLoggerWrapper = CachedLLMLoggerWrapper
		except ImportError:
			pass
			
		print("✓ BrowserUse LLM cache enabled - responses will be cached to ~/.cache/browseruse/llm/")
		
	except ImportError as e:
		print(f"⚠️  Failed to enable BrowserUse cache: {e}")
		print("Make sure browser_use is installed and available")


def disable_cache():
	"""Disable LLM response caching and restore original behavior."""
	try:
		from browser_use.agent import service
		
		# Restore original class if we have it
		if hasattr(service, '_original_LLMLoggerWrapper') and service._original_LLMLoggerWrapper:
			service.LLMLoggerWrapper = service._original_LLMLoggerWrapper
			
		# Also restore in logger_wrapper module
		try:
			from browser_use.llm import logger_wrapper
			if hasattr(service, '_original_LLMLoggerWrapper') and service._original_LLMLoggerWrapper:
				logger_wrapper.LLMLoggerWrapper = service._original_LLMLoggerWrapper
		except ImportError:
			pass
			
		print("✓ BrowserUse LLM cache disabled")
		
	except ImportError as e:
		print(f"⚠️  Failed to disable BrowserUse cache: {e}")


def clear_cache():
	"""Clear all cached LLM responses."""
	cache_dir = Path.home() / ".cache" / "browseruse" / "llm"
	
	if not cache_dir.exists():
		print("No cache directory found")
		return
		
	cache_files = list(cache_dir.glob("*.json"))
	for cache_file in cache_files:
		try:
			cache_file.unlink()
		except Exception:
			pass
	
	print(f"✓ Cleared {len(cache_files)} cached responses from {cache_dir}")


def cache_stats():
	"""Show cache statistics."""
	cache_dir = Path.home() / ".cache" / "browseruse" / "llm"
	
	if not cache_dir.exists():
		print("No cache directory found")
		return
		
	cache_files = list(cache_dir.glob("*.json"))
	total_size = sum(f.stat().st_size for f in cache_files)
	
	print(f"Cache directory: {cache_dir}")
	print(f"Cached responses: {len(cache_files)}")
	print(f"Total size: {total_size / 1024:.1f} KB")


if __name__ == "__main__":
	import sys
	
	if len(sys.argv) > 1:
		command = sys.argv[1]
		if command == "enable":
			enable_cache()
		elif command == "disable":
			disable_cache()
		elif command == "clear":
			clear_cache()
		elif command == "stats":
			cache_stats()
		else:
			print("Usage: python browser_use_cache_patch.py [enable|disable|clear|stats]")
	else:
		# Default action
		enable_cache()