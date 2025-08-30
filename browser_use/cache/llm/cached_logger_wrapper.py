"""
Cached LLM Logger Wrapper

This extends the existing LLMLoggerWrapper to add caching functionality.
It checks for cached responses before making LLM API calls and caches new responses.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Callable

from .cache import cache_response, get_cached_response
from browser_use.llm.logger_wrapper import LLMLoggerWrapper, _now_iso, _to_jsonable, _write_markdown_log
from browser_use.llm.views import ChatInvokeCompletion


class CachedLLMLoggerWrapper(LLMLoggerWrapper):
	"""
	Extends LLMLoggerWrapper to add response caching functionality.
	Checks cache before making API calls and stores responses for future use.
	"""

	_request_counter = 0  # Class-level counter for all instances

	def __init__(self, inner: Any, log_dir_provider: Callable[[], Path]):
		super().__init__(inner, log_dir_provider)

	async def ainvoke(self, messages, output_format=None):
		# Increment request counter
		CachedLLMLoggerWrapper._request_counter += 1
		request_num = CachedLLMLoggerWrapper._request_counter
		
		print(f"🔢 LLM REQUEST #{request_num}")
		
		# Check cache first
		cached_response = get_cached_response(self.model_name, messages)
		if cached_response:
			# Reconstruct the ChatInvokeCompletion object from cached data
			try:
				from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage
				
				# Reconstruct usage object
				usage_data = cached_response.get('usage')
				usage = None
				if usage_data:
					usage = ChatInvokeUsage(**usage_data)
				
				# Reconstruct completion object
				completion_data = cached_response.get('content')
				
				# Create proper ChatInvokeCompletion
				result = ChatInvokeCompletion(
					completion=completion_data,
					usage=usage,
					thinking=None,
					redacted_thinking=None
				)
				
				print(f"🎯 Using cached LLM response for request #{request_num}")
				return result
				
			except Exception as e:
				print(f"⚠️  Failed to reconstruct cached response: {e}, falling back to API call")
				# If reconstruction fails, fall through to actual API call
				pass

		# No cache hit, make actual API call
		start = _now_iso()
		req = {"messages": messages, "kwargs": {}}
		
		# Use the existing hash function from parent class for logging
		from browser_use.llm.logger_wrapper import _hash_request
		cache_key = _hash_request(self.model_name, messages, req["kwargs"])
		
		print(f"📝 Request #{request_num} - Cache key: {cache_key[:16]}...")

		try:
			result: ChatInvokeCompletion = await self._inner.ainvoke(messages, output_format)
			end = _now_iso()
			
			meta = {"start_time": start, "end_time": end}
			try:
				t0 = dt.datetime.fromisoformat(start)
				t1 = dt.datetime.fromisoformat(end)
				meta["duration_ms"] = int((t1 - t0).total_seconds() * 1000)
			except Exception:
				pass

			usage = getattr(result, "usage", None)
			if hasattr(usage, "model_dump"):
				usage = usage.model_dump()

			completion = getattr(result, "completion", None)
			if completion is not None:
				if hasattr(completion, "model_dump") and callable(getattr(completion, "model_dump")):
					try:
						completion = completion.model_dump()
					except Exception:
						completion = _to_jsonable(completion)
				elif hasattr(completion, "dict") and callable(getattr(completion, "dict")):
					try:
						completion = completion.dict()
					except Exception:
						completion = _to_jsonable(completion)
				else:
					completion = _to_jsonable(completion)

			resp = {
				"content": _to_jsonable(completion),
				"usage": _to_jsonable(usage),
				"error": None,
			}
			
			# Store in cache for future use
			cache_response(self.model_name, messages, resp)
			print(f"💾 Cached LLM response #{request_num} for future use")
			
			# Log with request number in filename
			self._write_numbered_markdown_log(request_num, cache_key, req, resp, meta)
			
			return result
			
		except Exception as e:
			end = _now_iso()
			meta = {"start_time": start, "end_time": end}
			resp = {"content": None, "usage": None, "error": str(e)}
			self._write_numbered_markdown_log(request_num, cache_key, req, resp, meta)
			raise
	
	def _write_numbered_markdown_log(self, request_num: int, cache_key: str, req: dict, resp: dict, meta: dict):
		"""Write log with request number in filename."""
		from browser_use.llm.logger_wrapper import _ensure_dir, _serialize_messages, _redact, _to_jsonable
		import datetime as dt
		import json
		
		log_dir = self._log_dir_provider()
		_ensure_dir(log_dir)
		
		ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:-3]
		short = cache_key[:8]
		# Include request number in filename
		path = log_dir / f"req_{request_num:03d}_{ts}-{self.model_name}-{short}.md"

		req_sanitized = {
			"model": self.model_name,
			"messages": _serialize_messages(req.get("messages")),
			"kwargs": _redact(req.get("kwargs")),
			"timestamp": meta.get("start_time"),
		}
		resp_sanitized = {
			"timestamp": meta.get("end_time"),
			"duration_ms": meta.get("duration_ms"),
			"usage": resp.get("usage"),
			"content": resp.get("content"),
			"error": resp.get("error"),
		}

		lines = []
		lines.append(f"# LLM Call #{request_num}")
		lines.append(f"- model: {self.model_name}")
		lines.append(f"- cache_key: {cache_key}")
		lines.append(f"- start: {meta.get('start_time')}")
		lines.append(f"- end: {meta.get('end_time')}")
		if meta.get("duration_ms") is not None:
			lines.append(f"- duration_ms: {meta['duration_ms']}")
		lines.append("")
		lines.append("## Request")
		lines.append("```json")
		lines.append(json.dumps(_to_jsonable(req_sanitized), indent=2, ensure_ascii=False, default=str))
		lines.append("```")
		lines.append("")
		lines.append("## Response")
		lines.append("```json")
		lines.append(json.dumps(_to_jsonable(resp_sanitized), indent=2, ensure_ascii=False, default=str))
		lines.append("```")
		lines.append("")

		path.write_text("\n".join(lines), encoding="utf-8")
		return path