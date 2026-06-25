#!/usr/bin/env python3
"""
ATLAS Pre-Request Hook for Claude Code
Analyzes user input for MITRE ATLAS threats before processing

Version: 1.0.0
Task: TIER 2D Task 27 (GAP-RES-008)

Integration:
    Add to ~/.claude/settings.json:
    {
        "hooks": {
            "PreToolUse": [{
                "command": "python3 ~/.claude/hooks/atlas_pre_request_hook.py"
            }]
        }
    }
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add tools directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "tools" / "security"))

try:
    from atlas_threat_detector import ATLASThreatDetector
except ImportError:
    # Fallback if import fails
    ATLASThreatDetector = None


def log_threat(result: dict, log_path: Path):
    """Log high-risk detections to security audit log."""
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "timestamp": result["timestamp"],
            "event": "ATLAS_THREAT_DETECTED",
            "risk": result["overall_risk"],
            "recommendation": result["recommendation"],
            "techniques": [d["technique_id"] for d in result["detections"]],
            "detection_count": result["detection_count"]
        }) + "\n")


def main():
    """Pre-request hook main function."""
    try:
        # Read input from stdin (Claude Code hook format)
        input_data = sys.stdin.read()

        if not input_data:
            # No input, allow request
            print(json.dumps({"status": "ALLOW", "reason": "no_input"}))
            return

        # Try to parse as JSON (hook format)
        try:
            data = json.loads(input_data)
            # Extract message from various possible fields
            user_message = (
                data.get("message", "") or
                data.get("content", "") or
                data.get("tool_input", {}).get("command", "") or
                str(data)
            )
        except json.JSONDecodeError:
            # Plain text input
            user_message = input_data

        if not user_message or not ATLASThreatDetector:
            print(json.dumps({"status": "ALLOW", "reason": "no_content_or_detector"}))
            return

        # Analyze for threats
        detector = ATLASThreatDetector()
        result = detector.analyze_input(user_message)

        # Log high-risk detections
        if result["overall_risk"] in ["HIGH", "CRITICAL"]:
            log_path = Path.home() / ".claude" / "security_audit.log"
            log_threat(result, log_path)

        # Output result
        output = {
            "status": result["recommendation"],
            "risk": result["overall_risk"],
            "detections": result["detection_count"],
            "techniques": [d["technique_id"] for d in result["detections"]]
        }
        print(json.dumps(output))

    except Exception as e:
        # On error, allow request but log error
        print(json.dumps({
            "status": "ALLOW",
            "error": str(e),
            "reason": "hook_error"
        }))


if __name__ == "__main__":
    main()
