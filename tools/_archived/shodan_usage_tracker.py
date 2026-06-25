#!/usr/bin/env python3
"""
Shodan API Usage Tracker

Tracks daily credit usage and alerts when approaching limits.
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Configuration
API_KEY = os.environ.get("SHODAN_API_KEY")  # <REDACTED — set env var SHODAN_API_KEY>
if not API_KEY:
    raise RuntimeError("SHODAN_API_KEY environment variable is not set")
LOG_FILE = Path("/home/user/.claude/logs/shodan_usage.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def get_account_info():
    """Get Shodan account information."""
    url = f"https://api.shodan.io/api-info?key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching account info: {e}", file=sys.stderr)
        return None

def log_usage(data):
    """Log usage to JSONL file."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "plan": data.get("plan"),
        "query_credits": data.get("query_credits"),
        "scan_credits": data.get("scan_credits"),
        "monitored_ips": data.get("monitored_ips"),
        "query_limit": data.get("usage_limits", {}).get("query_credits"),
        "scan_limit": data.get("usage_limits", {}).get("scan_credits"),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return log_entry

def check_alerts(data):
    """Check if credits are running low."""
    query_credits = data.get("query_credits", 0)
    scan_credits = data.get("scan_credits", 0)

    alerts = []

    # Alert thresholds
    if query_credits < 20:
        alerts.append(f"⚠️  LOW QUERY CREDITS: {query_credits}/100")
    elif query_credits < 50:
        alerts.append(f"ℹ️  Query credits: {query_credits}/100")

    if scan_credits < 20:
        alerts.append(f"⚠️  LOW SCAN CREDITS: {scan_credits}/100")

    return alerts

def get_usage_stats():
    """Calculate usage statistics from log file."""
    if not LOG_FILE.exists():
        return None

    entries = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                pass

    if not entries:
        return None

    # Get first and last entry
    first = entries[0]
    last = entries[-1]

    # Calculate usage
    query_used = first.get("query_credits", 100) - last.get("query_credits", 100)
    scan_used = first.get("scan_credits", 100) - last.get("scan_credits", 100)

    return {
        "tracking_since": first.get("timestamp"),
        "total_checks": len(entries),
        "query_credits_used": query_used,
        "scan_credits_used": scan_used,
    }

def main():
    """Main entry point."""
    print("=" * 60)
    print("SHODAN API USAGE TRACKER")
    print("=" * 60)
    print()

    # Get current account info
    data = get_account_info()
    if not data:
        print("❌ Failed to fetch account info")
        sys.exit(1)

    # Log usage
    entry = log_usage(data)

    # Display current status
    print(f"📊 Account Status:")
    print(f"   Plan: {entry['plan']}")
    print(f"   Query Credits: {entry['query_credits']}/{entry['query_limit']}")
    print(f"   Scan Credits: {entry['scan_credits']}/{entry['scan_limit']}")
    print(f"   Monitored IPs: {entry['monitored_ips']}/16")
    print()

    # Check for alerts
    alerts = check_alerts(data)
    if alerts:
        print("🔔 Alerts:")
        for alert in alerts:
            print(f"   {alert}")
        print()

    # Show usage statistics
    stats = get_usage_stats()
    if stats and stats["total_checks"] > 1:
        print(f"📈 Usage Statistics:")
        print(f"   Tracking Since: {stats['tracking_since'][:10]}")
        print(f"   Total Checks: {stats['total_checks']}")
        print(f"   Query Credits Used: {stats['query_credits_used']}")
        print(f"   Scan Credits Used: {stats['scan_credits_used']}")
        print()

    # Show log file location
    print(f"📝 Log File: {LOG_FILE}")
    print()

    print("=" * 60)

if __name__ == "__main__":
    main()
