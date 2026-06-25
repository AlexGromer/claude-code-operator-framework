#!/usr/bin/env python3
"""
Cache Validation Hook (GAP-CACHE-*)

PreToolUse hook that validates cache state before expensive operations.
Prevents stale cache issues and optimizes cache utilization.

Trigger: PreToolUse on WebFetch, WebSearch, Task
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from hashlib import md5

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
CACHE_STATE_FILE = DATA_DIR / "cache_state.json"
CACHE_LOG_FILE = DATA_DIR / "cache_validation.jsonl"

# Cache configuration
CACHE_CONFIG = {
    "WebFetch": {
        "ttl_minutes": 15,  # WebFetch has 15-minute cache
        "max_size_mb": 50,
    },
    "WebSearch": {
        "ttl_minutes": 30,  # Search results cache longer
        "max_size_mb": 20,
    },
    "Task": {
        "ttl_minutes": 60,  # Agent context caching
        "max_size_mb": 100,
    },
}


def load_cache_state() -> dict:
    """Load cache state from file."""
    if CACHE_STATE_FILE.exists():
        try:
            return json.loads(CACHE_STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "entries": {},
        "total_size_estimate": 0,
        "last_cleanup": None,
    }


def save_cache_state(state: dict):
    """Save cache state to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def generate_cache_key(tool_name: str, tool_input: dict) -> str:
    """Generate cache key from tool input."""
    # Create deterministic key
    key_data = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
    return md5(key_data.encode()).hexdigest()[:16]


def is_cache_valid(cache_key: str, tool_name: str, state: dict) -> tuple:
    """Check if cache entry is valid."""
    if cache_key not in state["entries"]:
        return False, "miss"

    entry = state["entries"][cache_key]
    config = CACHE_CONFIG.get(tool_name, {"ttl_minutes": 15})

    # Check TTL
    created = datetime.fromisoformat(entry["created"])
    expires = created + timedelta(minutes=config["ttl_minutes"])

    if datetime.now() > expires:
        return False, "expired"

    return True, "hit"


def estimate_request_size(tool_name: str, tool_input: dict) -> int:
    """Estimate response size in KB."""
    estimates = {
        "WebFetch": 500,  # ~500KB average page
        "WebSearch": 50,   # ~50KB search results
        "Task": 100,       # ~100KB agent response
    }
    return estimates.get(tool_name, 50)


def update_cache_entry(cache_key: str, tool_name: str, state: dict) -> dict:
    """Update or create cache entry."""
    estimated_size = estimate_request_size(tool_name, {})

    state["entries"][cache_key] = {
        "tool": tool_name,
        "created": datetime.now().isoformat(),
        "size_kb": estimated_size,
        "hits": state["entries"].get(cache_key, {}).get("hits", 0) + 1,
    }

    # Update total size estimate
    state["total_size_estimate"] = sum(
        e["size_kb"] for e in state["entries"].values()
    )

    return state


def cleanup_expired_entries(state: dict) -> dict:
    """Remove expired cache entries."""
    now = datetime.now()
    valid_entries = {}

    for key, entry in state["entries"].items():
        tool_name = entry.get("tool", "")
        config = CACHE_CONFIG.get(tool_name, {"ttl_minutes": 15})

        created = datetime.fromisoformat(entry["created"])
        expires = created + timedelta(minutes=config["ttl_minutes"])

        if now <= expires:
            valid_entries[key] = entry

    state["entries"] = valid_entries
    state["last_cleanup"] = now.isoformat()
    state["total_size_estimate"] = sum(
        e["size_kb"] for e in state["entries"].values()
    )

    return state


def log_validation(result: dict):
    """Log cache validation."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input_str = os.environ.get("CLAUDE_TOOL_INPUT", "{}")

    # Only process cacheable tools
    if tool_name not in CACHE_CONFIG:
        sys.exit(0)

    try:
        tool_input = json.loads(tool_input_str)
    except Exception:
        tool_input = {"raw": tool_input_str}

    # Load cache state
    state = load_cache_state()

    # Periodic cleanup
    if state.get("last_cleanup"):
        last_cleanup = datetime.fromisoformat(state["last_cleanup"])
        if datetime.now() - last_cleanup > timedelta(hours=1):
            state = cleanup_expired_entries(state)
    else:
        state = cleanup_expired_entries(state)

    # Generate cache key
    cache_key = generate_cache_key(tool_name, tool_input)

    # Check cache validity
    is_valid, status = is_cache_valid(cache_key, tool_name, state)

    # Update cache entry (for tracking)
    state = update_cache_entry(cache_key, tool_name, state)
    save_cache_state(state)

    # Log validation
    result = {
        "tool": tool_name,
        "cache_key": cache_key,
        "status": status,
        "total_entries": len(state["entries"]),
        "total_size_kb": state["total_size_estimate"],
    }
    log_validation(result)

    # Output cache status
    if status == "hit":
        output = {
            "cache_status": "potential_hit",
            "message": "Recent similar request may be cached",
            "ttl_remaining": CACHE_CONFIG[tool_name]["ttl_minutes"],
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
