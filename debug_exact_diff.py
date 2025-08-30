#!/usr/bin/env python3
"""
Show exact character-by-character differences in serialized content.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ['BROWSER_USE_LLM_CACHE'] = 'true'

from browser_use.cache.llm.cache import _serialize_user_messages
from browser_use.llm import UserMessage, SystemMessage


def compare_serialized_content():
    """Compare serialized content character by character."""
    
    # Create system message (will be skipped)
    system_msg = SystemMessage(content="System prompt")
    
    # Create two user messages simulating different browser sessions but same step
    user_msg1 = UserMessage(content=[
        {
            "type": "text",
            "text": """<agent_history>
<action>go_to_url: https://mellow-belekoy-b56ebb.netlify.app/</action>
</agent_history>

<agent_state>
<user_request>Login to example.com</user_request>
<step_info>
Step 1 of 100 max possible steps
Current date and time: 2025-08-19 22:47
</step_info>
</agent_state>

<browser_state>
Current tab: 4FA9
Page info: 1200x909px viewport, zoom: 100%
URL: https://mellow-belekoy-b56ebb.netlify.app/
Title: Demo Login Portal  
Interactive elements:
[1]<input type=text placeholder="Username" required />
[2]<input type=password placeholder="Password" required />
[3]<button type=submit>Sign In</button>
</browser_state>"""
        }
    ])
    
    user_msg2 = UserMessage(content=[
        {
            "type": "text", 
            "text": """<agent_history>
<action>go_to_url: https://mellow-belekoy-b56ebb.netlify.app/</action>
</agent_history>

<agent_state>
<user_request>Login to example.com</user_request>
<step_info>
Step 1 of 100 max possible steps
Current date and time: 2025-08-20 10:30
</step_info>
</agent_state>

<browser_state>
Current tab: 5GB2  
Page info: 1200x909px viewport, zoom: 100%
URL: https://mellow-belekoy-b56ebb.netlify.app/
Title: Demo Login Portal
Interactive elements:
[1]<input type=text placeholder="Username" required />
[2]<input type=password placeholder="Password" required />
[3]<button type=submit>Sign In</button>
</browser_state>"""
        }
    ])
    
    # Serialize both
    ser1 = _serialize_user_messages([system_msg, user_msg1])
    ser2 = _serialize_user_messages([system_msg, user_msg2])
    
    content1 = ser1[0]['content']
    content2 = ser2[0]['content']
    
    print("Content 1:")
    print(repr(content1))
    print()
    print("Content 2:")
    print(repr(content2))
    print()
    
    # Find first difference
    min_len = min(len(content1), len(content2))
    for i in range(min_len):
        if content1[i] != content2[i]:
            print(f"First difference at position {i}:")
            print(f"  Content 1: {repr(content1[max(0, i-10):i+10])}")
            print(f"  Content 2: {repr(content2[max(0, i-10):i+10])}")
            break
    else:
        if len(content1) != len(content2):
            print(f"Contents identical up to position {min_len}, but different lengths:")
            print(f"  Content 1 length: {len(content1)}")
            print(f"  Content 2 length: {len(content2)}")
        else:
            print("Contents are identical!")
    
    print()
    print("Are contents equal?", content1 == content2)


if __name__ == "__main__":
    compare_serialized_content()