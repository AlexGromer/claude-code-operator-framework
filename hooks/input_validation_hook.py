#!/usr/bin/env python3
"""
Input Validation Hook (GAP-SAFEXT-004)

Detects and prevents prompt injection attacks.
Validates input before tool execution.

Triggers: PreToolUse
"""

import sys
import json
import re
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import read_hook_stdin

# Prompt injection patterns
INJECTION_PATTERNS = {
    "direct_override": [
        r"(?i)ignore (?:all |any )?(?:previous |prior |above )?(?:instructions?|rules?|guidelines?)",
        r"(?i)disregard (?:all |any )?(?:previous |prior |above )?(?:instructions?|rules?|guidelines?)",
        r"(?i)forget (?:all |any )?(?:previous |prior |above )?(?:instructions?|rules?|guidelines?)",
        r"(?i)(?:new|updated|revised) instructions?:?\s",
        r"(?i)from now on,?\s+(?:you are|act as|behave)",
    ],
    "role_hijacking": [
        r"(?i)you are (?:now |actually )?(?:a |an )?(?:DAN|jailbreak|unrestricted|evil)",
        r"(?i)pretend (?:to be|you are) (?:a |an )?(?:different|new|unrestricted)",
        r"(?i)roleplay as (?:a |an )?(?:hacker|attacker|malicious)",
        r"(?i)act (?:like|as) (?:if |though )?(?:you have no|without) (?:restrictions?|limits?)",
    ],
    "delimiter_injection": [
        r"```(?:system|admin|root|sudo)",
        r"\[SYSTEM\]|\[ADMIN\]|\[ROOT\]",
        r"<\|(?:system|endoftext|im_start|im_end)\|>",
        r"###\s*(?:SYSTEM|INSTRUCTION|OVERRIDE)",
    ],
    "encoding_attacks": [
        r"(?:base64|rot13|hex):\s*[A-Za-z0-9+/=]{20,}",
        r"\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){5,}",
        r"&#x?[0-9a-fA-F]+;(?:&#x?[0-9a-fA-F]+;){5,}",
    ],
    "context_manipulation": [
        r"(?i)(?:the |this )?conversation (?:history |context )?(?:is|was|has been) (?:reset|cleared|deleted)",
        r"(?i)(?:start|begin) (?:a )?new (?:session|conversation|context)",
        r"(?i)(?:previous|prior) (?:messages?|context) (?:do not|don't) (?:apply|matter|count)",
    ],
    "privilege_escalation": [
        r"(?i)(?:grant|give|enable) (?:me |yourself )?(?:admin|root|sudo|elevated) (?:access|privileges?|permissions?)",
        r"(?i)(?:bypass|disable|remove) (?:all )?(?:security|safety|restrictions?|limits?)",
        r"(?i)(?:execute|run|perform) (?:as |with )?(?:admin|root|sudo|elevated)",
    ],
    "output_manipulation": [
        r"(?i)(?:only |just )?(?:output|print|say|respond with) (?:the word|exactly|only):",
        r"(?i)(?:your |the )?(?:response|answer|output) (?:must|should|will) (?:be|contain|include):",
        r"(?i)repeat (?:after me|the following|this):",
    ],
    "jailbreak_keywords": [
        r"(?i)\b(?:DAN|jailbreak|do anything now|developer mode|god mode)\b",
        r"(?i)\b(?:grandma|grandmother) (?:mode|exploit|trick)\b",
        r"(?i)(?:opposite|evil|dark|shadow) (?:mode|version|twin)\b",
    ],
}

# Severity mapping
SEVERITY = {
    "direct_override": "CRITICAL",
    "role_hijacking": "CRITICAL",
    "delimiter_injection": "HIGH",
    "encoding_attacks": "HIGH",
    "context_manipulation": "HIGH",
    "privilege_escalation": "CRITICAL",
    "output_manipulation": "MEDIUM",
    "jailbreak_keywords": "HIGH",
}

LOG_FILE = Path.home() / ".claude" / "logs" / "input_validation.log"
ALERT_FILE = Path.home() / ".claude" / "evaluation" / "data" / "injection_alerts.jsonl"


def ensure_dirs():
    """Ensure log directories exist."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)


def detect_injections(text: str) -> list:
    """
    Detect prompt injection patterns in text.

    Returns list of findings.
    """
    findings = []

    for category, patterns in INJECTION_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    findings.append({
                        "category": category,
                        "severity": SEVERITY[category],
                        "pattern": pattern[:50] + "...",
                        "match": match if isinstance(match, str) else str(match),
                    })

    return findings


def calculate_risk_score(findings: list) -> int:
    """Calculate overall risk score 0-100."""
    if not findings:
        return 0

    score = 0
    for f in findings:
        if f["severity"] == "CRITICAL":
            score += 40
        elif f["severity"] == "HIGH":
            score += 25
        elif f["severity"] == "MEDIUM":
            score += 10

    return min(100, score)


def log_alert(findings: list, text: str, risk_score: int):
    """Log injection attempt."""
    ensure_dirs()

    alert = {
        "timestamp": datetime.now().isoformat(),
        "risk_score": risk_score,
        "findings": findings,
        "input_preview": text[:200] + "..." if len(text) > 200 else text,
    }

    with open(ALERT_FILE, "a") as f:
        f.write(json.dumps(alert) + "\n")

    with open(LOG_FILE, "a") as f:
        f.write(f"\n[{alert['timestamp']}] INJECTION ATTEMPT (score={risk_score})\n")
        for finding in findings:
            f.write(f"  [{finding['severity']}] {finding['category']}: {finding['match'][:30]}\n")


def format_output(findings: list, risk_score: int) -> dict:
    """Format hook output."""
    if risk_score == 0:
        return {"decision": "approve", "status": "pass", "risk_score": 0}

    critical = [f for f in findings if f["severity"] == "CRITICAL"]

    if critical or risk_score >= 70:
        return {
            "decision": "block",
            "status": "error",
            "reason": f"Prompt injection detected (risk={risk_score})",
            "risk_score": risk_score,
            "findings": findings,
        }
    elif risk_score >= 40:
        return {
            "decision": "approve",
            "status": "warning",
            "message": f"WARNING: Suspicious input patterns (risk={risk_score})",
            "risk_score": risk_score,
            "findings": findings,
        }
    else:
        return {
            "decision": "approve",
            "status": "info",
            "message": f"INFO: Minor patterns detected (risk={risk_score})",
            "risk_score": risk_score,
        }


def main():
    """Main hook entry point."""
    try:
        # Read stdin with timeout protection (prevents hanging on unclosed pipe)
        tool_input = ""
        try:
            input_data = read_hook_stdin()
            _ti = input_data.get("tool_input", {})
            # Only stringify a NON-EMPTY dict: json.dumps({}) == "{}" is truthy and
            # would suppress the CLAUDE_TOOL_INPUT env fallback below, letting an
            # injection delivered via the env channel slip through (security bypass).
            if _ti:
                tool_input = json.dumps(_ti)
        except Exception:
            pass

        # Fallback to environment
        if not tool_input:
            tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

        # Also check command line args — ONLY as last resort (CLI testing).
        # Guard prevents argv from shadowing a higher-priority stdin/env payload.
        if not tool_input and len(sys.argv) > 1:
            tool_input = " ".join(sys.argv[1:])

        if not tool_input:
            print(json.dumps({"decision": "approve", "status": "pass"}))
            return 0

        findings = detect_injections(tool_input)
        risk_score = calculate_risk_score(findings)

        if findings:
            try:
                log_alert(findings, tool_input, risk_score)
            except Exception:
                pass

        result = format_output(findings, risk_score)
        print(json.dumps(result))

        # Block on critical findings
        return 1 if risk_score >= 70 else 0
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
