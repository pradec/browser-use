# BrowserUse LLM Response Cache

This cache system avoids redundant LLM API calls by storing responses locally and reusing them for identical requests.

## Features

- **Automatic caching** of all LLM responses
- **Smart key generation** that ignores timestamps and other dynamic content
- **Filesystem storage** in `~/.cache/browseruse/llm/`
- **Zero configuration** - just enable and use
- **Non-invasive** - uses monkey patching, no core code changes needed
- **Cache management** commands for stats, clearing, etc.

## Quick Start

### Method 1: Use the enhanced run_task script

```bash
# Enable caching and run a task
python run_task_with_cache.py --prompt "Navigate to example.com and tell me the title"

# Run the same task again - should be much faster due to caching
python run_task_with_cache.py --prompt "Navigate to example.com and tell me the title"
```

### Method 2: Enable caching in your own scripts

```python
# Enable caching before importing browser_use
import browser_use_cache_patch
browser_use_cache_patch.enable_cache()

# Now use BrowserUse normally - responses will be cached automatically
from browser_use import Agent
from browser_use.llm import ChatOpenAI

agent = Agent(
    task="Your task here",
    llm=ChatOpenAI(model="gpt-4o-mini")
)
result = await agent.run()
```

## How it Works

### Cache Key Generation
The cache generates keys based on:
- **Model name** (different models = different cache entries)
- **User message content** (the varying part of requests)
- **Masked dynamic content** (timestamps, step numbers, etc. are normalized)

### What Gets Masked
To ensure consistent cache keys across runs, these dynamic elements are masked:
- Timestamps (`2025-08-19T17:17:31.872166+00:00` → `[TIMESTAMP]`)
- Current date/time (`Current date and time: 2025-08-19 22:47` → `Current date and time: [MASKED]`)
- Step numbers (`Step 7 of 100` → `Step [X] of [Y]`)
- Agent/session IDs (`browser_use_agent_068a4b19...` → `browser_use_agent_[MASKED]`)
- Temporary paths (`/var/folders/...` → `[TEMP_PATH]`)
- Image data (replaced with `[IMAGE_MASKED]`)
- Page dimensions (`1200x909px` → `[SIZE]px`)

### System Prompt Handling
- System prompts are **excluded** from cache keys (they're static and large)
- Only user messages and their content determine cache hits

## Cache Management

### View cache statistics
```bash
python browser_use_cache_patch.py stats
```

### Clear all cached responses
```bash
python browser_use_cache_patch.py clear
```

### Enable/disable caching
```bash
python browser_use_cache_patch.py enable
python browser_use_cache_patch.py disable
```

### Programmatic management
```python
import browser_use_cache_patch

# Show stats
browser_use_cache_patch.cache_stats()

# Clear cache  
browser_use_cache_patch.clear_cache()

# Enable/disable
browser_use_cache_patch.enable_cache()
browser_use_cache_patch.disable_cache()
```

## Testing the Cache

### Test with a simple task:

1. **First run** (will make LLM calls and cache responses):
   ```bash
   python run_task_with_cache.py --prompt test_task.md
   ```

2. **Second run** (should use cached responses and be much faster):
   ```bash
   python run_task_with_cache.py --prompt test_task.md
   ```

3. **Check cache stats**:
   ```bash
   python browser_use_cache_patch.py stats
   ```

### Expected behavior:
- First run: Normal speed, shows "💾 Cached LLM response for future use"
- Second run: Much faster, shows "🎯 Using cached LLM response"
- Cache directory contains `.json` files with responses

## File Structure

```
~/.cache/browseruse/llm/           # Cache directory
├── a1b2c3d4e5f6...json           # Cached responses (MD5 filenames)
├── f6e5d4c3b2a1...json
└── ...

browser_use/llm/
├── cache.py                      # Core cache logic
├── cached_logger_wrapper.py      # Cached version of logger wrapper
└── ...

browser_use_cache_patch.py        # Monkey patch integration
run_task_with_cache.py            # Enhanced run_task with caching
```

## Implementation Details

### Integration Architecture
- **Monkey patches** `LLMLoggerWrapper` in `browser_use.agent.service`
- **Extends** existing logging infrastructure 
- **Preserves** all existing functionality
- **No changes** to core BrowserUse code required

### Cache Storage Format
Each cached response is stored as JSON:
```json
{
  "content": { ... },              // The actual LLM response
  "usage": {                       // Token usage stats
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  },
  "error": null
}
```

### Error Handling
- **Cache failures** don't break execution (fail silently)
- **Malformed cache** files are ignored
- **Missing cache** directory is created automatically
- **Reconstruction errors** fall back to real API calls

## Requirements

- Python 3.11+
- BrowserUse library
- Standard library only (no additional dependencies)

## Notes

- Cache keys are **deterministic** - same input always produces same key
- Cache is **persistent** across Python sessions
- Cache **never expires** (manual clearing required)
- Cache works with **all LLM providers** supported by BrowserUse
- **Thread-safe** for concurrent access

## Troubleshooting

**Cache not working?**
- Ensure `BROWSER_USE_LLM_CALL_LOGS=true` is set (done automatically)
- Check cache directory permissions: `~/.cache/browseruse/llm/`
- Verify monkey patch loaded before BrowserUse imports

**Cache too aggressive?**
- Different models create separate cache entries
- Small changes in user prompts create different keys
- System prompts don't affect caching (intentional)

**Cache growing too large?**
- Use `python browser_use_cache_patch.py clear` to clean up
- Each response is typically 1-10KB
- Cache directory location: `~/.cache/browseruse/llm/`