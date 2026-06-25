#!/usr/bin/env python3
"""
Hook Health Checker (GAP-HOOKS-HEALTH)

Monitors hook health, execution times, and error rates.
Detects problematic hooks that may slow down operations.

Usage:
    python hook_health_checker.py --status
    python hook_health_checker.py --check
    python hook_health_checker.py --stats
    python hook_health_checker.py --verify HOOK_NAME
    python hook_health_checker.py --benchmark
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import time

HOOKS_DIR = Path.home() / ".claude" / "hooks"
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
SETTINGS_FILE = Path.home() / ".claude" / "settings.json"
HEALTH_LOG = DATA_DIR / "hook_health.jsonl"
STATS_FILE = DATA_DIR / "hook_stats.json"

# Health thresholds
THRESHOLDS = {
    "max_execution_ms": 2000,      # Max single execution time
    "avg_execution_ms": 500,       # Target average execution
    "max_error_rate": 0.05,        # Max 5% error rate
    "min_success_rate": 0.95,      # Min 95% success rate
}


@dataclass
class HookHealth:
    """Hook health status."""
    name: str
    path: str
    exists: bool
    executable: bool
    syntax_valid: bool
    registered: bool
    trigger_type: str  # PreToolUse, PostToolUse, etc.
    last_execution: Optional[str]
    avg_execution_ms: float
    error_rate: float
    total_executions: int
    status: str  # healthy, warning, critical, unknown


def load_settings() -> Dict:
    """Load Claude settings."""
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {}


def load_stats() -> Dict:
    """Load hook statistics."""
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except Exception:
            pass
    return {"hooks": {}, "last_updated": None}


def save_stats(stats: Dict):
    """Save hook statistics."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stats["last_updated"] = datetime.now().isoformat()
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def get_registered_hooks() -> Dict[str, List[Dict]]:
    """Get hooks registered in settings.json."""
    settings = load_settings()
    hooks_config = settings.get("hooks", {})

    registered = {}
    for trigger_type in ["PreToolUse", "PostToolUse", "SessionStart", "SessionEnd"]:
        if trigger_type in hooks_config:
            for matcher in hooks_config[trigger_type]:
                for hook in matcher.get("hooks", []):
                    command = hook.get("command", "")
                    # Extract hook script path
                    if "~/.claude/hooks/" in command or "/home/" in command:
                        # Extract filename
                        parts = command.split()
                        for part in parts:
                            if ".py" in part:
                                hook_path = part.replace("~", str(Path.home()))
                                hook_name = Path(hook_path).stem
                                registered[hook_name] = {
                                    "path": hook_path,
                                    "trigger_type": trigger_type,
                                    "command": command,
                                    "timeout": hook.get("timeout", 5000),
                                    "blocking": hook.get("blocking", False),
                                }

    return registered


def get_hook_files() -> List[Path]:
    """Get all hook files in hooks directory."""
    if not HOOKS_DIR.exists():
        return []

    return list(HOOKS_DIR.glob("*_hook.py")) + list(HOOKS_DIR.glob("*.py"))


def check_syntax(hook_path: Path) -> bool:
    """Check Python syntax validity."""
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", str(hook_path)],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def benchmark_hook(hook_path: Path, iterations: int = 3) -> Dict:
    """Benchmark hook execution time."""
    times = []

    for _ in range(iterations):
        start = time.time()
        try:
            result = subprocess.run(
                ["python", str(hook_path)],
                capture_output=True,
                timeout=5,
                env={
                    **os.environ,
                    "CLAUDE_TOOL_NAME": "Test",
                    "CLAUDE_TOOL_INPUT": "{}",
                    "CLAUDE_TOOL_OUTPUT": "test output",
                }
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        except subprocess.TimeoutExpired:
            times.append(5000)  # Timeout
        except Exception:
            times.append(-1)  # Error

    valid_times = [t for t in times if t > 0]
    return {
        "avg_ms": round(sum(valid_times) / len(valid_times), 2) if valid_times else -1,
        "min_ms": round(min(valid_times), 2) if valid_times else -1,
        "max_ms": round(max(valid_times), 2) if valid_times else -1,
        "errors": len([t for t in times if t < 0]),
        "timeouts": len([t for t in times if t >= 5000]),
    }


def check_hook_health(hook_path: Path, registered_hooks: Dict) -> HookHealth:
    """Check health of a single hook."""
    hook_name = hook_path.stem
    stats = load_stats()
    hook_stats = stats.get("hooks", {}).get(hook_name, {})

    health = HookHealth(
        name=hook_name,
        path=str(hook_path),
        exists=hook_path.exists(),
        executable=os.access(hook_path, os.X_OK),
        syntax_valid=check_syntax(hook_path) if hook_path.exists() else False,
        registered=hook_name in registered_hooks,
        trigger_type=registered_hooks.get(hook_name, {}).get("trigger_type", "unknown"),
        last_execution=hook_stats.get("last_execution"),
        avg_execution_ms=hook_stats.get("avg_execution_ms", 0),
        error_rate=hook_stats.get("error_rate", 0),
        total_executions=hook_stats.get("total_executions", 0),
        status="unknown",
    )

    # Determine status
    if not health.exists:
        health.status = "critical"
    elif not health.syntax_valid:
        health.status = "critical"
    elif not health.registered:
        health.status = "warning"
    elif health.error_rate > THRESHOLDS["max_error_rate"]:
        health.status = "critical"
    elif health.avg_execution_ms > THRESHOLDS["max_execution_ms"]:
        health.status = "warning"
    elif health.avg_execution_ms > THRESHOLDS["avg_execution_ms"]:
        health.status = "warning"
    else:
        health.status = "healthy"

    return health


def get_all_hooks_health() -> List[HookHealth]:
    """Get health status of all hooks."""
    registered = get_registered_hooks()
    hook_files = get_hook_files()

    # Check file-based hooks
    healths = []
    checked_names = set()

    for hook_path in hook_files:
        health = check_hook_health(hook_path, registered)
        healths.append(health)
        checked_names.add(hook_path.stem)

    # Check registered hooks that don't exist as files
    for hook_name, config in registered.items():
        if hook_name not in checked_names:
            hook_path = Path(config["path"])
            health = check_hook_health(hook_path, registered)
            healths.append(health)

    return sorted(healths, key=lambda h: (
        {"critical": 0, "warning": 1, "healthy": 2, "unknown": 3}[h.status],
        h.name
    ))


def get_overall_health() -> Dict:
    """Get overall hooks health summary."""
    healths = get_all_hooks_health()

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_hooks": len(healths),
        "by_status": {
            "healthy": len([h for h in healths if h.status == "healthy"]),
            "warning": len([h for h in healths if h.status == "warning"]),
            "critical": len([h for h in healths if h.status == "critical"]),
            "unknown": len([h for h in healths if h.status == "unknown"]),
        },
        "by_trigger": {},
        "issues": [],
        "overall_status": "healthy",
    }

    # Count by trigger type
    for health in healths:
        trigger = health.trigger_type
        if trigger not in summary["by_trigger"]:
            summary["by_trigger"][trigger] = 0
        summary["by_trigger"][trigger] += 1

    # Collect issues
    for health in healths:
        if health.status == "critical":
            summary["issues"].append({
                "hook": health.name,
                "issue": "Critical health issue",
                "details": f"exists={health.exists}, syntax={health.syntax_valid}, error_rate={health.error_rate}",
            })
        elif health.status == "warning":
            summary["issues"].append({
                "hook": health.name,
                "issue": "Warning",
                "details": f"registered={health.registered}, avg_ms={health.avg_execution_ms}",
            })

    # Determine overall status
    if summary["by_status"]["critical"] > 0:
        summary["overall_status"] = "critical"
    elif summary["by_status"]["warning"] > summary["total_hooks"] * 0.3:
        summary["overall_status"] = "warning"

    return summary


def log_health_check(result: Dict):
    """Log health check result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_LOG, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def print_health_status(healths: List[HookHealth]):
    """Print health status table."""
    print("\n" + "="*80)
    print("HOOK HEALTH STATUS")
    print("="*80)

    status_icons = {
        "healthy": "🟢",
        "warning": "🟡",
        "critical": "🔴",
        "unknown": "⚪",
    }

    for health in healths:
        icon = status_icons[health.status]
        print(f"\n{icon} {health.name}")
        print(f"   Status: {health.status.upper()}")
        print(f"   Path: {health.path}")
        print(f"   Registered: {'Yes' if health.registered else 'No'}")
        print(f"   Trigger: {health.trigger_type}")
        print(f"   Syntax Valid: {'Yes' if health.syntax_valid else 'No'}")
        if health.total_executions > 0:
            print(f"   Executions: {health.total_executions}")
            print(f"   Avg Time: {health.avg_execution_ms}ms")
            print(f"   Error Rate: {health.error_rate:.1%}")

    print("\n" + "="*80)


def print_summary(summary: Dict):
    """Print health summary."""
    print("\n" + "="*60)
    print("HOOKS HEALTH SUMMARY")
    print("="*60)

    status_icons = {
        "healthy": "🟢",
        "warning": "🟡",
        "critical": "🔴",
    }

    print(f"\nOverall Status: {status_icons.get(summary['overall_status'], '⚪')} {summary['overall_status'].upper()}")
    print(f"Total Hooks: {summary['total_hooks']}")

    print("\nBy Status:")
    for status, count in summary["by_status"].items():
        print(f"  {status_icons.get(status, '⚪')} {status}: {count}")

    print("\nBy Trigger:")
    for trigger, count in summary["by_trigger"].items():
        print(f"  {trigger}: {count}")

    if summary["issues"]:
        print("\nIssues:")
        for issue in summary["issues"][:5]:
            print(f"  ⚠️ {issue['hook']}: {issue['issue']}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Hook Health Checker")
    parser.add_argument("--status", "-s", action="store_true", help="Show health status of all hooks")
    parser.add_argument("--check", "-c", action="store_true", help="Run health check")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--verify", "-v", help="Verify specific hook")
    parser.add_argument("--benchmark", "-b", action="store_true", help="Benchmark all hooks")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.verify:
        hook_path = HOOKS_DIR / f"{args.verify}.py"
        if not hook_path.exists():
            hook_path = HOOKS_DIR / args.verify
        if not hook_path.exists():
            print(f"❌ Hook not found: {args.verify}")
            return 1

        registered = get_registered_hooks()
        health = check_hook_health(hook_path, registered)

        if args.json:
            print(json.dumps(asdict(health), indent=2))
        else:
            print_health_status([health])

        # Run benchmark
        print("\nRunning benchmark...")
        benchmark = benchmark_hook(hook_path)
        print(f"  Avg: {benchmark['avg_ms']}ms")
        print(f"  Min: {benchmark['min_ms']}ms")
        print(f"  Max: {benchmark['max_ms']}ms")
        print(f"  Errors: {benchmark['errors']}")

        return 0

    if args.benchmark:
        print("\nBenchmarking all hooks...")
        hook_files = get_hook_files()

        results = []
        for hook_path in hook_files:
            print(f"  Testing {hook_path.stem}...", end="", flush=True)
            benchmark = benchmark_hook(hook_path, iterations=3)
            print(f" {benchmark['avg_ms']}ms")
            results.append({
                "hook": hook_path.stem,
                **benchmark
            })

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\nBenchmark Results:")
            for r in sorted(results, key=lambda x: x["avg_ms"], reverse=True):
                status = "🔴" if r["avg_ms"] > THRESHOLDS["max_execution_ms"] else "🟢"
                print(f"  {status} {r['hook']}: {r['avg_ms']}ms (min: {r['min_ms']}, max: {r['max_ms']})")

        return 0

    if args.check or args.status:
        healths = get_all_hooks_health()
        summary = get_overall_health()

        log_health_check(summary)

        if args.json:
            print(json.dumps({
                "summary": summary,
                "hooks": [asdict(h) for h in healths],
            }, indent=2))
        else:
            print_summary(summary)
            if args.status:
                print_health_status(healths)

        return 0

    if args.stats:
        stats = load_stats()
        summary = get_overall_health()

        if args.json:
            print(json.dumps({
                "stats": stats,
                "summary": summary,
            }, indent=2))
        else:
            print_summary(summary)

        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
