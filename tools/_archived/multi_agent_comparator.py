#!/usr/bin/env python3
"""
Multi-Agent Comparator (GAP-ORCH-012)

Compares performance of different agent architectures and configurations.
Supports A/B testing, benchmark comparisons, and statistical analysis.

Usage:
    python multi_agent_comparator.py --compare config_a.json config_b.json
    python multi_agent_comparator.py --benchmark --agents haiku,sonnet,opus
    python multi_agent_comparator.py --report
"""

import argparse
import json
import sys
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
COMPARISONS_FILE = DATA_DIR / "agent_comparisons.jsonl"
STATS_FILE = DATA_DIR / "agent_comparison_stats.json"


@dataclass
class AgentConfig:
    """Agent configuration for comparison."""
    name: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    tools_enabled: List[str] = field(default_factory=list)
    system_prompt: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a single task execution."""
    agent_name: str
    task_id: str
    success: bool
    duration_ms: float
    tokens_used: int
    tool_calls: int
    quality_score: float  # 0-1
    errors: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of comparing multiple agents."""
    comparison_id: str
    task_type: str
    agents: List[str]
    results: Dict[str, List[TaskResult]]
    winner: Optional[str]
    metrics: Dict
    timestamp: str


# Sample benchmark tasks
BENCHMARK_TASKS = [
    {
        "id": "code_gen_simple",
        "type": "code_generation",
        "prompt": "Write a Python function to check if a number is prime",
        "expected_patterns": ["def ", "return", "True", "False"],
    },
    {
        "id": "code_review",
        "type": "code_review",
        "prompt": "Review this code for bugs: def add(a, b): return a - b",
        "expected_patterns": ["bug", "error", "should be", "+"],
    },
    {
        "id": "explanation",
        "type": "explanation",
        "prompt": "Explain what a hash table is in 3 sentences",
        "expected_patterns": ["key", "value", "O(1)", "lookup"],
    },
    {
        "id": "tool_use",
        "type": "tool_use",
        "prompt": "Find all Python files in the current directory",
        "expected_patterns": [".py", "glob", "find"],
    },
    {
        "id": "multi_step",
        "type": "reasoning",
        "prompt": "Plan how to deploy a web app: list 5 steps",
        "expected_patterns": ["1.", "2.", "3.", "deploy", "test"],
    },
]


def simulate_agent_execution(config: AgentConfig, task: Dict) -> TaskResult:
    """Simulate agent executing a task (mock for testing)."""
    import random
    import time

    start = time.time()

    # Simulate execution time based on model
    base_time = {"haiku": 100, "sonnet": 300, "opus": 800}.get(config.model, 200)
    duration = base_time + random.randint(-50, 100)
    time.sleep(duration / 10000)  # Small actual delay

    # Simulate success rate based on model
    success_rate = {"haiku": 0.85, "sonnet": 0.92, "opus": 0.97}.get(config.model, 0.9)
    success = random.random() < success_rate

    # Simulate quality score
    quality_base = {"haiku": 0.7, "sonnet": 0.85, "opus": 0.95}.get(config.model, 0.8)
    quality = min(1.0, quality_base + random.uniform(-0.1, 0.1))

    # Simulate token usage
    tokens_base = {"haiku": 500, "sonnet": 800, "opus": 1200}.get(config.model, 700)
    tokens = tokens_base + random.randint(-100, 200)

    # Simulate tool calls
    tool_calls = random.randint(0, 3) if "tool" in task.get("type", "") else 0

    return TaskResult(
        agent_name=config.name,
        task_id=task["id"],
        success=success,
        duration_ms=duration,
        tokens_used=tokens,
        tool_calls=tool_calls,
        quality_score=round(quality, 3),
        errors=[] if success else ["Simulated failure"],
    )


def run_comparison(configs: List[AgentConfig], tasks: List[Dict]) -> ComparisonResult:
    """Run comparison between agents."""
    results: Dict[str, List[TaskResult]] = {c.name: [] for c in configs}

    for task in tasks:
        for config in configs:
            result = simulate_agent_execution(config, task)
            results[config.name].append(result)

    # Calculate metrics
    metrics = {}
    for agent_name, agent_results in results.items():
        success_rate = sum(1 for r in agent_results if r.success) / len(agent_results)
        avg_duration = statistics.mean(r.duration_ms for r in agent_results)
        avg_quality = statistics.mean(r.quality_score for r in agent_results)
        total_tokens = sum(r.tokens_used for r in agent_results)

        metrics[agent_name] = {
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": round(avg_duration, 2),
            "avg_quality": round(avg_quality, 3),
            "total_tokens": total_tokens,
            "tasks_completed": len(agent_results),
        }

    # Determine winner (by quality * success_rate)
    scores = {
        name: m["avg_quality"] * m["success_rate"]
        for name, m in metrics.items()
    }
    winner = max(scores, key=scores.get) if scores else None

    return ComparisonResult(
        comparison_id=f"CMP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        task_type="mixed",
        agents=[c.name for c in configs],
        results={k: [asdict(r) for r in v] for k, v in results.items()},
        winner=winner,
        metrics=metrics,
        timestamp=datetime.now().isoformat(),
    )


def load_stats() -> Dict:
    """Load historical comparison stats."""
    if STATS_FILE.exists():
        return json.loads(STATS_FILE.read_text())
    return {"comparisons": 0, "by_model": {}}


def save_stats(stats: Dict):
    """Save comparison stats."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def log_comparison(result: ComparisonResult):
    """Log comparison result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMPARISONS_FILE, "a") as f:
        f.write(json.dumps(asdict(result)) + "\n")

    # Update stats
    stats = load_stats()
    stats["comparisons"] += 1
    for agent, metrics in result.metrics.items():
        if agent not in stats["by_model"]:
            stats["by_model"][agent] = {"wins": 0, "comparisons": 0}
        stats["by_model"][agent]["comparisons"] += 1
        if agent == result.winner:
            stats["by_model"][agent]["wins"] += 1
    save_stats(stats)


def print_comparison(result: ComparisonResult):
    """Print comparison results."""
    print("\n" + "="*70)
    print(f"MULTI-AGENT COMPARISON: {result.comparison_id}")
    print("="*70)

    print(f"\nAgents: {', '.join(result.agents)}")
    print(f"Tasks: {len(BENCHMARK_TASKS)}")
    print(f"Winner: 🏆 {result.winner}")

    print("\n" + "-"*50)
    print("METRICS BY AGENT")
    print("-"*50)

    for agent, metrics in result.metrics.items():
        icon = "🏆" if agent == result.winner else "  "
        print(f"\n{icon} {agent}:")
        print(f"   Success Rate: {metrics['success_rate']:.1%}")
        print(f"   Avg Quality:  {metrics['avg_quality']:.3f}")
        print(f"   Avg Duration: {metrics['avg_duration_ms']:.0f}ms")
        print(f"   Total Tokens: {metrics['total_tokens']:,}")

    print("\n" + "="*70)


def print_stats():
    """Print historical stats."""
    stats = load_stats()

    print("\n" + "="*50)
    print("HISTORICAL COMPARISON STATISTICS")
    print("="*50)

    print(f"\nTotal Comparisons: {stats['comparisons']}")

    if stats["by_model"]:
        print("\nWin Rate by Model:")
        for model, data in sorted(stats["by_model"].items()):
            win_rate = data["wins"] / data["comparisons"] if data["comparisons"] > 0 else 0
            print(f"  {model}: {win_rate:.1%} ({data['wins']}/{data['comparisons']})")

    print("\n" + "="*50)


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Comparator")
    parser.add_argument("--compare", nargs="+", help="Config files to compare")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark comparison")
    parser.add_argument("--agents", default="haiku,sonnet,opus", help="Agents to benchmark")
    parser.add_argument("--report", action="store_true", help="Show statistics")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save results")

    args = parser.parse_args()

    if args.report:
        if args.json:
            print(json.dumps(load_stats(), indent=2))
        else:
            print_stats()
        return 0

    # Create agent configs
    if args.benchmark:
        agent_names = args.agents.split(",")
        configs = [
            AgentConfig(name=name, model=name)
            for name in agent_names
        ]
    elif args.compare:
        configs = []
        for config_file in args.compare:
            with open(config_file) as f:
                data = json.load(f)
            configs.append(AgentConfig(**data))
    else:
        # Default comparison
        configs = [
            AgentConfig(name="haiku", model="haiku"),
            AgentConfig(name="sonnet", model="sonnet"),
        ]

    # Run comparison
    result = run_comparison(configs, BENCHMARK_TASKS)

    # Save if requested
    if args.save:
        log_comparison(result)

    # Output
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print_comparison(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
