#!/usr/bin/env python3
"""
OSINT Cache Hook — Auto-save MCP OSINT tool results

Automatically caches results from:
- Shodan (mcp__shodan__)
- WHOIS lookups
- DNS queries
- Subdomain discovery
- Other OSINT tools

Results organized by target (domain/IP/username) in /opt/work/osint/cache/
"""

import sys
import json
import os
import re
from datetime import datetime
from pathlib import Path

# Configuration
CACHE_DIR = Path("/opt/work/osint/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def extract_target(tool_name: str, tool_input: str) -> str:
    """
    Extract target (domain, IP, username) from tool input.

    Returns normalized target name for directory organization.
    """
    # Parse tool_input JSON
    try:
        if tool_input:
            input_data = json.loads(tool_input)
        else:
            input_data = {}
    except (json.JSONDecodeError, TypeError):
        input_data = {"raw": tool_input}

    # Extract target based on tool type
    target = None

    # Shodan tools
    if "shodan" in tool_name:
        # Search for IP, domain, or query
        if "host" in tool_name or "ip" in input_data:
            target = input_data.get("ip") or input_data.get("host")
        elif "search" in tool_name or "query" in input_data:
            query = input_data.get("query", "")
            # Extract domain or IP from query
            domain_match = re.search(r'\b([a-z0-9-]+\.)+[a-z]{2,}\b', query, re.I)
            ip_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', query)
            target = domain_match.group(0) if domain_match else (ip_match.group(0) if ip_match else None)

    # WHOIS/DNS tools
    elif any(keyword in tool_name for keyword in ["whois", "dns", "dig"]):
        target = input_data.get("domain") or input_data.get("query")

    # Username OSINT (sherlock, maigret, etc.)
    elif any(keyword in tool_name for keyword in ["sherlock", "maigret", "username"]):
        target = input_data.get("username") or input_data.get("user")

    # Generic: look for common parameter names
    if not target:
        for param in ["target", "domain", "ip", "host", "query", "username"]:
            if param in input_data:
                target = input_data[param]
                break

    # Fallback: sanitize raw input
    if not target and isinstance(input_data.get("raw"), str):
        # Extract first domain/IP/word from raw input
        raw = input_data["raw"]
        domain_match = re.search(r'\b([a-z0-9-]+\.)+[a-z]{2,}\b', raw, re.I)
        ip_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', raw)
        word_match = re.search(r'\b[a-z0-9_-]{3,}\b', raw, re.I)
        target = (domain_match or ip_match or word_match).group(0) if (domain_match or ip_match or word_match) else None

    # Normalize target (lowercase, remove special chars)
    if target:
        target = re.sub(r'[^\w.-]', '_', target.lower())

    return target or "unknown"

def get_tool_type(tool_name: str) -> str:
    """Determine tool type from tool name."""
    if "shodan" in tool_name:
        return "shodan"
    elif "whois" in tool_name:
        return "whois"
    elif "dns" in tool_name or "dig" in tool_name:
        return "dns"
    elif "sherlock" in tool_name or "maigret" in tool_name:
        return "username"
    elif "subdomain" in tool_name or "subfinder" in tool_name or "amass" in tool_name:
        return "subdomains"
    elif "crt.sh" in tool_name or "certificate" in tool_name:
        return "crt_sh"
    elif "github" in tool_name:
        return "github"
    else:
        return "osint"

def save_cache(target: str, tool_type: str, data: dict):
    """Save OSINT result to cache."""
    # Create target directory
    target_dir = CACHE_DIR / target
    target_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"{tool_type}_{timestamp}.json"
    filepath = target_dir / filename

    # Save JSON
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(filepath)

def main():
    """Main hook entry point."""
    try:
        # Read stdin (PostToolUse hook receives tool info via stdin)
        stdin_data = sys.stdin.read()

        # Get environment variables
        tool_name = os.getenv("CLAUDE_TOOL_NAME", "")
        tool_input = os.getenv("CLAUDE_TOOL_INPUT", "")
        tool_output = os.getenv("CLAUDE_TOOL_OUTPUT", "")

        # Only cache MCP OSINT tools
        if not tool_name.startswith("mcp__"):
            sys.exit(0)

        # Check if this is an OSINT-related tool
        osint_tools = ["shodan", "whois", "dns", "dig", "sherlock", "maigret",
                       "subfinder", "amass", "crt", "github"]
        if not any(keyword in tool_name.lower() for keyword in osint_tools):
            sys.exit(0)

        # Extract target
        target = extract_target(tool_name, tool_input)

        # Determine tool type
        tool_type = get_tool_type(tool_name)

        # Parse tool output
        try:
            output_data = json.loads(tool_output) if tool_output else {}
        except json.JSONDecodeError:
            output_data = {"raw_output": tool_output}

        # Create cache entry
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "target": target,
            "input": json.loads(tool_input) if tool_input else {},
            "output": output_data
        }

        # Save to cache
        filepath = save_cache(target, tool_type, cache_entry)

        # Log success (optional, for debugging)
        # print(f"[OSINT_CACHE] Saved: {filepath}", file=sys.stderr)

    except Exception as e:
        # Silent fail — don't block Claude Code execution
        # Uncomment for debugging:
        # print(f"[OSINT_CACHE] Error: {e}", file=sys.stderr)
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()
