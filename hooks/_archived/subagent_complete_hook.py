#!/usr/bin/env python3
"""
Subagent Completion Hook (GAP-ORCHESTRATION-*)

PostToolUse hook that tracks subagent completion and performance.
Validates output quality and tracks orchestration patterns.

Trigger: PostToolUse on Task tool
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "subagent_completions.jsonl"
STATS_FILE = DATA_DIR / "subagent_stats.json"

# Output quality indicators
QUALITY_INDICATORS = {
    "positive": [
        r'completed successfully',
        r'task completed',
        r'found \d+ ',
        r'created',
        r'updated',
        r'verified',
        r'✓|✅',
    ],
    "negative": [
        r'failed',
        r'error',
        r'could not',
        r'unable to',
        r'not found',
        r'❌|⚠️',
    ],
}

# Model cost weights (relative)
MODEL_COSTS = {
    "haiku": 1,
    "sonnet": 15,
    "opus": 75,
}


def parse_task_input(tool_input: dict) -> dict:
    """Parse Task tool input."""
    return {
        "subagent_type": tool_input.get("subagent_type", "unknown"),
        "model": tool_input.get("model", "sonnet"),
        "description": tool_input.get("description", ""),
        "prompt_length": len(tool_input.get("prompt", "")),
        "run_in_background": tool_input.get("run_in_background", False),
    }


def assess_output_quality(output: str) -> dict:
    """Assess subagent output quality."""
    assessment = {
        "quality_score": 0.5,  # Base score
        "positive_signals": 0,
        "negative_signals": 0,
        "output_length": len(output),
    }

    # Check positive indicators
    for pattern in QUALITY_INDICATORS["positive"]:
        if re.search(pattern, output, re.IGNORECASE):
            assessment["positive_signals"] += 1

    # Check negative indicators
    for pattern in QUALITY_INDICATORS["negative"]:
        if re.search(pattern, output, re.IGNORECASE):
            assessment["negative_signals"] += 1

    # Calculate quality score
    positive_boost = min(assessment["positive_signals"] * 0.1, 0.4)
    negative_penalty = min(assessment["negative_signals"] * 0.15, 0.5)

    assessment["quality_score"] = round(
        max(0.1, min(1.0, 0.5 + positive_boost - negative_penalty)), 3
    )

    # Assess output completeness
    if assessment["output_length"] < 50:
        assessment["quality_score"] *= 0.7
        assessment["completeness"] = "minimal"
    elif assessment["output_length"] < 200:
        assessment["completeness"] = "brief"
    elif assessment["output_length"] < 1000:
        assessment["completeness"] = "adequate"
    else:
        assessment["completeness"] = "comprehensive"

    return assessment


def update_stats(task_info: dict, quality: dict):
    """Update aggregate statistics."""
    stats = {"by_type": {}, "by_model": {}, "total": 0}
    if STATS_FILE.exists():
        try:
            stats = json.loads(STATS_FILE.read_text())
        except Exception:
            pass

    # Update by type
    agent_type = task_info["subagent_type"]
    if agent_type not in stats["by_type"]:
        stats["by_type"][agent_type] = {
            "count": 0,
            "avg_quality": 0,
            "total_quality": 0,
        }

    type_stats = stats["by_type"][agent_type]
    type_stats["count"] += 1
    type_stats["total_quality"] += quality["quality_score"]
    type_stats["avg_quality"] = round(
        type_stats["total_quality"] / type_stats["count"], 3
    )

    # Update by model
    model = task_info["model"]
    if model not in stats["by_model"]:
        stats["by_model"][model] = {
            "count": 0,
            "avg_quality": 0,
            "total_quality": 0,
            "estimated_cost_units": 0,
        }

    model_stats = stats["by_model"][model]
    model_stats["count"] += 1
    model_stats["total_quality"] += quality["quality_score"]
    model_stats["avg_quality"] = round(
        model_stats["total_quality"] / model_stats["count"], 3
    )
    model_stats["estimated_cost_units"] += MODEL_COSTS.get(model, 15)

    stats["total"] += 1
    stats["last_updated"] = datetime.now().isoformat()

    # Save stats
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

    return stats


def log_completion(result: dict):
    """Log subagent completion."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input_str = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    # Only process Task tool
    if tool_name != "Task":
        sys.exit(0)

    # Parse input
    try:
        tool_input = json.loads(tool_input_str)
    except Exception:
        tool_input = {}

    task_info = parse_task_input(tool_input)

    # Assess output quality
    quality = assess_output_quality(tool_output)

    # Update statistics
    update_stats(task_info, quality)

    # Log completion
    result = {
        "subagent_type": task_info["subagent_type"],
        "model": task_info["model"],
        "description": task_info["description"][:50],
        "prompt_length": task_info["prompt_length"],
        "output_length": quality["output_length"],
        "quality_score": quality["quality_score"],
        "completeness": quality["completeness"],
        "positive_signals": quality["positive_signals"],
        "negative_signals": quality["negative_signals"],
    }
    log_completion(result)

    # Output summary if quality is low
    if quality["quality_score"] < 0.4:
        output = {
            "status": "subagent_quality_alert",
            "quality_score": quality["quality_score"],
            "completeness": quality["completeness"],
            "negative_signals": quality["negative_signals"],
            "recommendation": "Consider reviewing subagent output or retrying",
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
