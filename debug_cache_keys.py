#!/usr/bin/env python3
"""
Debug script to examine what cache keys are being generated and why they differ.
"""

import json
import os
import sys
from pathlib import Path

# Set up environment
sys.path.insert(0, str(Path(__file__).parent))
os.environ['BROWSER_USE_LLM_CACHE'] = 'true'

from browser_use.cache.llm.cache import _serialize_user_messages, _generate_cache_key, _mask_dynamic_content


def debug_cache_key_generation():
    """Add debugging to the cache key generation process."""
    
    # Let's monkey patch the cache generation to log what's being processed
    original_generate_key = _generate_cache_key
    
    def debug_generate_key(model, messages):
        print(f"\n🔍 CACHE KEY DEBUG")
        print(f"Model: {model}")
        print(f"Number of messages: {len(messages)}")
        
        for i, msg in enumerate(messages):
            print(f"\nMessage {i+1}:")
            print(f"  Role: {getattr(msg, 'role', 'unknown')}")
            print(f"  Type: {type(msg)}")
            
            if hasattr(msg, 'model_dump'):
                data = msg.model_dump()
                print(f"  Content type: {type(data.get('content', 'unknown'))}")
                if isinstance(data.get('content'), list):
                    print(f"  Content parts: {len(data['content'])}")
                    for j, part in enumerate(data['content']):
                        if isinstance(part, dict):
                            print(f"    Part {j+1}: {part.get('type', 'unknown')} ({len(str(part)) if part.get('type') != 'image_url' else 'image'} chars)")
                elif isinstance(data.get('content'), str):
                    print(f"  Content length: {len(data['content'])} chars")
                    print(f"  Content preview: {repr(data['content'][:100])}...")
        
        # Show serialized messages
        serialized = _serialize_user_messages(messages)
        print(f"\n📝 SERIALIZED FOR CACHE:")
        print(f"Number of user messages: {len(serialized)}")
        
        for i, msg in enumerate(serialized):
            print(f"\nSerialized message {i+1}:")
            print(f"  Role: {msg.get('role')}")
            content = msg.get('content', '')
            print(f"  Content length: {len(content)}")
            print(f"  Content preview: {repr(content[:200])}...")
            if len(content) > 200:
                print(f"  Content end: ...{repr(content[-100:])}")
        
        # Generate and return key
        key = original_generate_key(model, messages)
        print(f"\n🔑 Generated cache key: {key}")
        return key
    
    # Monkey patch
    import browser_use.cache.llm.cache
    browser_use.cache.llm.cache._generate_cache_key = debug_generate_key
    
    print("🐒 Cache key generation debugging enabled!")
    return debug_generate_key


if __name__ == "__main__":
    debug_cache_key_generation()
    print("Debug patches applied. Now run your BrowserUse task to see cache key details.")