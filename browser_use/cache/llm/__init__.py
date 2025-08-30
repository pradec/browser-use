"""
LLM Response Cache System

This module provides LLM response caching functionality for BrowserUse.
Caching is controlled by the BROWSER_USE_LLM_CACHE environment variable.
"""

import os


def is_cache_enabled() -> bool:
	"""Check if LLM caching is enabled via environment variable."""
	return os.environ.get('BROWSER_USE_LLM_CACHE', '').lower() in ('true', '1', 'yes', 'on')


def enable_cache():
	"""Enable LLM caching by setting environment variable."""
	os.environ['BROWSER_USE_LLM_CACHE'] = 'true'


def disable_cache():
	"""Disable LLM caching by clearing environment variable."""
	os.environ.pop('BROWSER_USE_LLM_CACHE', None)


# Only expose cache functionality if caching is enabled
if is_cache_enabled():
	from .cache import get_cached_response, cache_response, cache_stats, clear_cache
	from .cached_logger_wrapper import CachedLLMLoggerWrapper
	
	__all__ = [
		'is_cache_enabled',
		'enable_cache', 
		'disable_cache',
		'get_cached_response',
		'cache_response',
		'cache_stats',
		'clear_cache',
		'CachedLLMLoggerWrapper'
	]
else:
	__all__ = [
		'is_cache_enabled',
		'enable_cache',
		'disable_cache'
	]