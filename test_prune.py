import sys
import os

# Create dummy for testing
def prune_history(history: list, limit: int = 30000) -> list:
    if not history:
        return []
    
    # Always keep system prompt (first message if it's system)
    if history and history[0].get("role") == "system":
        system_msg = history[0]
        messages = history[1:]
    else:
        system_msg = None
        messages = history
    
    # Calculate total length
    total_length = sum(len(str(msg.get("content", ""))) for msg in history)
    
    # If under limit, return all
    if total_length <= limit:
        return history
    
    # Remove oldest messages until under limit
    while messages and total_length > limit:
        removed = messages.pop(0)
        total_length -= len(str(removed.get("content", "")))
    
    # Reconstruct history
    result = []
    if system_msg:
        result.append(system_msg)
    result.extend(messages)
    
    return result

history = [
    {"role": "system", "content": "a" * 1000},
    {"role": "user", "content": "b" * 30000}
]

print(prune_history(history, 30000))
