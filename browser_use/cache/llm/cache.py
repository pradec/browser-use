"""
LLM Response Cache System for BrowserUse

This module provides a filesystem-based cache for LLM responses to avoid redundant API calls.
The cache stores responses in ~/.cache/browseruse/llm/ using MD5 hashes as filenames.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from browser_use.llm.messages import BaseMessage


def _get_cache_dir() -> Path:
	"""Get the cache directory, creating it if it doesn't exist."""
	cache_dir = Path.home() / ".cache" / "browseruse" / "llm"
	cache_dir.mkdir(parents=True, exist_ok=True)
	return cache_dir


def _mask_dynamic_content(content: str) -> str:
	"""Mask only timestamps and tab IDs to ensure cache consistency."""
	# Mask timestamps and dates only
	content = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}', '[TIMESTAMP]', content)
	content = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', '[DATETIME]', content)
	content = re.sub(r'Current date and time: [^\n]+', 'Current date and time: [MASKED]', content)
	
	# Mask tab IDs (alphanumeric strings after "Current tab:") and normalize trailing spaces
	content = re.sub(r'Current tab: [A-Za-z0-9]+\s*', 'Current tab: [TAB_ID]', content)
	
	# Normalize whitespace - remove trailing spaces on lines
	content = re.sub(r' +\n', '\n', content)
	content = re.sub(r' +$', '', content, flags=re.MULTILINE)
	
	return content


def _serialize_user_messages(messages: list[BaseMessage]) -> list[Dict[str, Any]]:
	"""Serialize only user messages with text content, skip screenshots, mask timestamps only."""
	user_messages = []
	
	for message in messages:
		# Only process user messages
		if getattr(message, 'role', None) != 'user':
			continue
			
		# Get the content
		if hasattr(message, 'model_dump'):
			msg_data = message.model_dump()
		else:
			msg_data = {'role': 'user', 'content': str(message)}
		
		# Extract only text content, skip images/screenshots
		content = msg_data.get('content', '')
		if isinstance(content, list):
			# Multi-part content - extract only text parts, skip image_url parts
			text_parts = []
			for part in content:
				if isinstance(part, dict) and part.get('type') == 'text':
					text_parts.append(part.get('text', ''))
			# Combine all text parts
			combined_text = '\n'.join(text_parts)
		elif isinstance(content, str):
			combined_text = content
		else:
			combined_text = str(content)
		
		# Mask only timestamps in the combined text
		masked_content = _mask_dynamic_content(combined_text)
		
		# Create simplified cache entry with just the essential fields
		cache_entry = {
			'role': 'user',
			'content': masked_content
		}
		
		user_messages.append(cache_entry)
	
	return user_messages


def _generate_cache_key(model: str, messages: list[BaseMessage]) -> str:
	"""Generate a cache key based on model and masked user message content."""
	user_messages = _serialize_user_messages(messages)
	
	cache_payload = {
		'model': model,
		'messages': user_messages
	}
	
	# Create deterministic JSON string
	json_str = json.dumps(cache_payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
	
	# Generate MD5 hash
	return hashlib.md5(json_str.encode('utf-8')).hexdigest()


def _is_cache_enabled() -> bool:
	"""Check if LLM caching is enabled via environment variable."""
	return os.environ.get('BROWSER_USE_LLM_CACHE', '').lower() in ('true', '1', 'yes', 'on')


def get_cached_response(model: str, messages: list[BaseMessage]) -> Dict[str, Any] | None:
	"""Try to retrieve a cached response for the given model and messages."""
	if not _is_cache_enabled():
		return None
		
	try:
		cache_key = _generate_cache_key(model, messages)
		cache_file = _get_cache_dir() / f"{cache_key}.json"
		
		if cache_file.exists():
			with open(cache_file, 'r', encoding='utf-8') as f:
				return json.load(f)
	except Exception:
		# If anything goes wrong with cache retrieval, fail silently
		pass
	
	return None


def cache_response(model: str, messages: list[BaseMessage], response: Dict[str, Any]) -> None:
	"""Store a response in the cache."""
	if not _is_cache_enabled():
		return
		
	try:
		cache_key = _generate_cache_key(model, messages)
		cache_file = _get_cache_dir() / f"{cache_key}.json"
		
		with open(cache_file, 'w', encoding='utf-8') as f:
			json.dump(response, f, indent=2, ensure_ascii=False)
	except Exception:
		# If caching fails, continue without caching (don't break the flow)
		pass


def cache_stats():
	"""Show cache statistics."""
	cache_dir = _get_cache_dir()
	
	if not cache_dir.exists():
		print("No cache directory found")
		return
		
	cache_files = list(cache_dir.glob("*.json"))
	total_size = sum(f.stat().st_size for f in cache_files)
	
	print(f"Cache directory: {cache_dir}")
	print(f"Cached responses: {len(cache_files)}")
	print(f"Total size: {total_size / 1024:.1f} KB")


def clear_cache():
	"""Clear all cached LLM responses."""
	cache_dir = _get_cache_dir()
	
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