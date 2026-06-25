#!/usr/bin/env python3
"""
Hook Benchmark Tool — Measures latency of all registered hooks.

Usage:
    python hook_benchmark.py                  # Benchmark all hooks
    python hook_benchmark.py --event Bash     # Benchmark hooks for specific tool
    python hook_benchmark.py --iterations 5   # Custom iteration count

Results from v6.0 optimization (2026-02-25):
    Before cleanup: ~1872ms total per Bash call (9 PreToolUse + 13 PostToolUse)
    After cleanup:  ~430ms total per Bash call (3 PreToolUse + 3 PostToolUse)
    Savings: -77% latency, -55% hook registrations (33→14)
"""

import json
import subprocess
import sys
import time
from pathlib import Path

HOOKS_DIR = Path.home() / ".claude" / "hooks"
EVAL_HOOKS_DIR = Path.home() / ".claude" / "evaluation" / "hooks"

# Current registered hooks (v6.0, 14 registrations in settings.json)
HOOKS = {
    "PreToolUse": [
        HOOKS_DIR / "input_validation_hook.py",
        HOOKS_DIR / "hitl_approval_hook.py",
        EVAL_HOOKS_DIR / "unified_budget_hook.py",
    ],
    "PostToolUse": [
        HOOKS_DIR / "unified_tool_metrics_hook.py",
        HOOKS_DIR / "unified_cost_hook.py",
        HOOKS_DIR / "code_review_hook.py",
    ],
    "SessionStart": [
        HOOKS_DIR / "session_start_reinforcement.py",
    ],
    "SessionEnd": [
        HOOKS_DIR / "session_end_hook.py",
    ],
    "UserPromptSubmit": [
        HOOKS_DIR / "user_prompt_submit_hook.py",
    ],
    "PreCompact": [
        HOOKS_DIR / "pre_compact_hook.py",
    ],
    "PostToolUseFailure": [
        HOOKS_DIR / "tool_failure_hook.py",
    ],
}

TEST_INPUTS = {
    "PreToolUse": {"tool_name": "Bash", "tool_input": {"command": "echo test"}},
    "PostToolUse": {"tool_name": "Bash", "tool_input": {"command": "echo test"}, "tool_result": "test"},
    "SessionStart": {},
    "SessionEnd": {},
    "UserPromptSubmit": {"user_prompt": "test prompt"},
    "PreCompact": {"context_info": {}},
    "PostToolUseFailure": {"tool_name": "Bash", "error": "test error"},
}


def benchmark_hook(hook_path: Path, event: str, iterations: int = 3) -> dict:
    """Benchmark a single hook, return avg/min/max in ms."""
    if not hook_path.exists():
        return {"path": str(hook_path), "status": "MISSING", "avg_ms": 0}

    test_input = json.dumps(TEST_INPUTS.get(event, {}))
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            subprocess.run(
                [sys.executable, str(hook_path)],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=5,
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        except subprocess.TimeoutExpired:
            times.append(5000)
        except Exception as e:
            return {"path": str(hook_path), "status": f"ERROR: {e}", "avg_ms": 0}

    return {
        "path": str(hook_path.name),
        "status": "OK",
        "avg_ms": round(sum(times) / len(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark Claude Code hooks")
    parser.add_argument("--event", help="Filter by event type (e.g., PreToolUse)")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per hook")
    args = parser.parse_args()

    iterations = args.iterations
    total_pre = 0
    total_post = 0

    print(f"Hook Benchmark (v6.0, {iterations} iterations each)")
    print("=" * 70)

    for event, hooks in HOOKS.items():
        if args.event and args.event not in event:
            continue

        print(f"\n{event} ({len(hooks)} hooks):")
        for hook_path in hooks:
            result = benchmark_hook(hook_path, event, iterations)
            status = result["status"]
            avg = result["avg_ms"]

            if status == "OK":
                color = "  " if avg < 200 else "! " if avg < 500 else "!!"
                print(f"  {color} {result['path']:40s} avg={avg:7.1f}ms  min={result['min_ms']:.1f}  max={result['max_ms']:.1f}")
                if event == "PreToolUse":
                    total_pre += avg
                elif event == "PostToolUse":
                    total_post += avg
            else:
                print(f"  ?? {result['path']:40s} {status}")

    print(f"\n{'=' * 70}")
    print(f"Total PreToolUse (per tool call):  {total_pre:.0f}ms")
    print(f"Total PostToolUse (per tool call): {total_post:.0f}ms")
    print(f"Combined overhead per Bash call:   {total_pre + total_post:.0f}ms")
    print(f"\nThresholds: <500ms OK | 500-2000ms optimize | >2000ms consolidate")


if __name__ == "__main__":
    main()
