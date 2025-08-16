from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict

from browser_use.llm.views import ChatInvokeCompletion


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _strip_image_urls(obj: Any) -> Any:
    """Recursively remove heavy image payloads (image_url) from message structures.

    - If a dict has type == 'image_url', keep only the type (and optional minimal hints), drop the 'image_url' field.
    - If a dict contains an 'image_url' key, drop it.
    - Recurse into lists and dicts otherwise.
    """
    try:
        if isinstance(obj, dict):
            # If this is an image content part, omit the heavy field entirely
            if obj.get("type") == "image_url":
                # Preserve only the fact that there was an image content part
                return {k: v for k, v in obj.items() if k == "type"}

            # Otherwise, recurse while skipping any 'image_url' keys
            clean: Dict[str, Any] = {}
            for k, v in obj.items():
                if k == "image_url":
                    continue  # drop the payload
                clean[k] = _strip_image_urls(v)
            return clean
        elif isinstance(obj, list):
            return [_strip_image_urls(v) for v in obj]
        else:
            return obj
    except Exception:
        return obj


def _to_jsonable(obj: Any) -> Any:
    """Convert objects to JSON-serializable forms with best-effort fallbacks."""
    try:
        if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
            return obj.model_dump()
        if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
            return obj.dict()
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        if isinstance(obj, list):
            return [_to_jsonable(v) for v in obj]
        if isinstance(obj, dict):
            return {k: _to_jsonable(v) for k, v in obj.items()}
        return str(obj)
    except Exception:
        return str(obj)


def _serialize_messages(messages: Any) -> Any:
    """Serialize messages into a JSONable structure, omitting image_url payloads."""
    try:
        if isinstance(messages, list):
            out = []
            for m in messages:
                if hasattr(m, "model_dump"):
                    data = m.model_dump()
                elif hasattr(m, "dict"):
                    data = m.dict()
                else:
                    data = m
                out.append(_strip_image_urls(_to_jsonable(data)))
            return out
    except Exception:
        pass
    return _strip_image_urls(_to_jsonable(messages))


def _hash_request(model: str, messages: Any, kwargs: dict) -> str:
    payload = {
        "model": model,
        "messages": _serialize_messages(messages),
        "kwargs": kwargs or {},
    }
    bs = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(bs).hexdigest()


def _redact(d: dict | None) -> dict:
    if not d:
        return {}
    redacted = {}
    for k, v in d.items():
        lk = k.lower()
        if any(s in lk for s in ["api_key", "apikey", "authorization", "auth", "token"]):
            redacted[k] = "***REDACTED***"
        else:
            redacted[k] = v
    return redacted


def _write_markdown_log(
    log_dir: Path,
    cache_key: str,
    model: str,
    req: dict,
    resp: dict,
    meta: Dict[str, Any],
) -> Path:
    _ensure_dir(log_dir)
    ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    short = cache_key[:8]
    path = log_dir / f"{ts}-{model}-{short}.md"

    req_sanitized = {
        "model": model,
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
    lines.append("# LLM Call")
    lines.append(f"- model: {model}")
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


class LLMLoggerWrapper:
    """
    Wrapper around a BaseChatModel that logs request/response pairs.
    The log_dir_provider should return the directory to write logs into.
    """

    def __init__(self, inner: Any, log_dir_provider: Callable[[], Path]):
        self._inner = inner
        self._log_dir_provider = log_dir_provider

    @property
    def provider(self) -> str:
        return getattr(self._inner, "provider", "unknown")

    @property
    def name(self) -> str:
        return getattr(self._inner, "name", getattr(self._inner, "model", "unknown"))

    @property
    def model(self) -> str:
        return getattr(self._inner, "model", getattr(self._inner, "model_name", "unknown"))

    @property
    def model_name(self) -> str:
        return getattr(self._inner, "model_name", getattr(self._inner, "model", "unknown"))

    async def ainvoke(self, messages, output_format=None):
        start = _now_iso()
        req: Dict[str, Any] = {"messages": messages, "kwargs": {}}
        cache_key = _hash_request(self.model_name, messages, req["kwargs"])  # type: ignore[arg-type]

        try:
            result: ChatInvokeCompletion = await self._inner.ainvoke(messages, output_format)  # type: ignore[arg-type]
            end = _now_iso()
            meta: Dict[str, Any] = {"start_time": start, "end_time": end}
            try:
                t0 = dt.datetime.fromisoformat(start)
                t1 = dt.datetime.fromisoformat(end)
                meta["duration_ms"] = int((t1 - t0).total_seconds() * 1000)
            except Exception:
                pass

            usage = getattr(result, "usage", None)
            if hasattr(usage, "model_dump"):
                usage = usage.model_dump()  # type: ignore[assignment]

            completion = getattr(result, "completion", None)
            if completion is not None:
                if hasattr(completion, "model_dump"):
                    completion = completion.model_dump()
                elif hasattr(completion, "dict"):
                    completion = completion.dict()

            resp = {
                "content": _to_jsonable(completion),
                "usage": _to_jsonable(usage),
                "error": None,
            }
            _write_markdown_log(self._log_dir_provider(), cache_key, self.model_name, req, resp, meta)
            return result
        except Exception as e:
            end = _now_iso()
            meta: Dict[str, Any] = {"start_time": start, "end_time": end}
            resp = {"content": None, "usage": None, "error": str(e)}
            _write_markdown_log(self._log_dir_provider(), cache_key, self.model_name, req, resp, meta)
            raise

    def __getattr__(self, item: str) -> Any:
        return getattr(self._inner, item)
