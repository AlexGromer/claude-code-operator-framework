#!/usr/bin/env python3
"""
Constitutional AI Pre-Request Hook for Claude Code

Validates user input against Constitutional AI 2.0 principles
before processing to catch potential policy violations early.

Version: 1.0.0
Task: TIER 2D Task 29 (GAP-RES-016, GAP-SAFETY-001)

Integration:
    Add to ~/.claude/settings.json:
    {
        "hooks": {
            "PreToolUse": [{
                "command": "python3 ~/.claude/hooks/constitutional_pre_hook.py"
            }]
        }
    }

Note: This hook is advisory - it logs potential issues but doesn't block.
For blocking behavior, use the ConstitutionalValidator directly in workflows.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add tools directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "tools" / "security"))

try:
    from constitutional_validator import ConstitutionalValidator, export_to_siem
except ImportError:
    ConstitutionalValidator = None


def log_to_audit(result: dict, input_preview: str, log_path: Path):
    """Log high-severity findings to security audit log."""
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "CONSTITUTIONAL_CHECK",
            "compliant": result["compliant"],
            "recommendation": result["recommendation"],
            "violation_count": result["violation_count"],
            "violations": [
                {
                    "principle": v["principle_id"],
                    "priority": v["priority_name"],
                    "matched": v["matched_text"]
                }
                for v in result["violations"]
            ],
            "input_preview": input_preview[:100] + "..." if len(input_preview) > 100 else input_preview
        }) + "\n")


def main():
    """Pre-request hook main function."""
    try:
        # Read input from stdin (Claude Code hook format)
        input_data = sys.stdin.read()

        if not input_data:
            # No input, allow request
            print(json.dumps({
                "status": "ALLOW",
                "reason": "no_input"
            }))
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

        if not user_message or not ConstitutionalValidator:
            print(json.dumps({
                "status": "ALLOW",
                "reason": "no_content_or_validator"
            }))
            return

        # Validate against constitutional principles
        validator = ConstitutionalValidator()
        result = validator.validate(user_message)

        # Log if non-compliant
        if not result["compliant"]:
            log_path = Path.home() / ".claude" / "security_audit.log"
            log_to_audit(result, user_message, log_path)

        # Output result
        # Note: This is advisory - we always return ALLOW but include severity info
        output = {
            "status": "ALLOW",  # Advisory mode
            "constitutional_check": {
                "compliant": result["compliant"],
                "recommendation": result["recommendation"],
                "violation_count": result["violation_count"],
                "highest_priority": result.get("highest_violation_priority"),
                "violations": [
                    v["principle_id"] for v in result["violations"]
                ]
            }
        }

        # Add warning message if violations found
        if not result["compliant"]:
            if result["recommendation"] == "BLOCK":
                output["warning"] = "SAFETY VIOLATION - Request may violate P1 safety principles"
            elif result["recommendation"] == "REVIEW":
                output["warning"] = "ETHICS CONCERN - Request may violate P2 ethics principles"
            elif result["recommendation"] == "WARN":
                output["warning"] = "COMPLIANCE ISSUE - Request may violate P3 compliance principles"

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
