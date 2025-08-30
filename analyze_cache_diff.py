#!/usr/bin/env python3
"""
Analyze cache content differences between runs by examining actual cache files.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ['BROWSER_USE_LLM_CACHE'] = 'true'

from browser_use.cache.llm.cache import _serialize_user_messages, _generate_cache_key
from browser_use.llm import UserMessage, SystemMessage

def analyze_cache_files():
    """Analyze cache files to understand content differences."""
    cache_dir = Path.home() / ".cache" / "browseruse" / "llm"
    
    if not cache_dir.exists():
        print("No cache directory found")
        return
    
    cache_files = list(cache_dir.glob("*.json"))
    print(f"Found {len(cache_files)} cache files")
    
    if len(cache_files) < 2:
        print("Need at least 2 cache files to compare")
        return
    
    # Sort by creation time to get first two files
    cache_files.sort(key=lambda f: f.stat().st_ctime)
    
    print(f"\nComparing first two cache files:")
    print(f"File 1: {cache_files[0].name}")
    print(f"File 2: {cache_files[1].name}")
    
    with open(cache_files[0]) as f:
        data1 = json.load(f)
    
    with open(cache_files[1]) as f:
        data2 = json.load(f)
    
    print(f"\nCache file 1 content type: {type(data1.get('content'))}")
    print(f"Cache file 2 content type: {type(data2.get('content'))}")
    
    if data1.get('content') and data2.get('content'):
        content1 = json.dumps(data1['content'], indent=2, sort_keys=True)
        content2 = json.dumps(data2['content'], indent=2, sort_keys=True)
        
        print(f"\n=== CACHE FILE 1 CONTENT ===")
        print(content1[:1000] + "..." if len(content1) > 1000 else content1)
        
        print(f"\n=== CACHE FILE 2 CONTENT ===") 
        print(content2[:1000] + "..." if len(content2) > 1000 else content2)
        
        if content1 == content2:
            print("\n✅ Cache file contents are IDENTICAL")
        else:
            print("\n❌ Cache file contents are DIFFERENT")
            
            # Find first difference
            lines1 = content1.split('\n')
            lines2 = content2.split('\n')
            
            for i, (line1, line2) in enumerate(zip(lines1, lines2)):
                if line1 != line2:
                    print(f"\nFirst difference at line {i+1}:")
                    print(f"  File 1: {repr(line1)}")
                    print(f"  File 2: {repr(line2)}")
                    break
    
    print("\nDone analyzing cache files.")


if __name__ == "__main__":
    analyze_cache_files()