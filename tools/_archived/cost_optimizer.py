#!/usr/bin/env python3
"""
Cost Optimizer (GAP-COST-001)

Analyzes and optimizes agent costs based on model usage patterns.
Provides recommendations for model selection and cost reduction.

Usage:
    python cost_optimizer.py --analyze
    python cost_optimizer.py --recommend TASK_TYPE
    python cost_optimizer.py --simulate MODEL TOKENS
    python cost_optimizer.py --report
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
COST_DIR = DATA_DIR / "cost_optimizer"
USAGE_FILE = COST_DIR / "usage_log.jsonl"
RECOMMENDATIONS_FILE = COST_DIR / "recommendations.json"


# Pricing per 1M tokens (approximate, for demonstration)
MODEL_PRICING = {
    "haiku": {"input": 0.25, "output": 1.25},
    "sonnet": {"input": 3.0, "output": 15.0},
    "opus": {"input": 15.0, "output": 75.0},
}

# Model capabilities (score 1-10)
MODEL_CAPABILITIES = {
    "haiku": {"speed": 10, "quality": 6, "reasoning": 5, "code": 6},
    "sonnet": {"speed": 7, "quality": 8, "reasoning": 8, "code": 8},
    "opus": {"speed": 4, "quality": 10, "reasoning": 10, "code": 9},
}

# Task type to recommended model mapping
TASK_RECOMMENDATIONS = {
    "simple_formatting": {"model": "haiku", "reason": "Low complexity, high speed needed"},
    "data_extraction": {"model": "haiku", "reason": "Structured output, minimal reasoning"},
    "code_generation": {"model": "sonnet", "reason": "Good balance of quality and cost"},
    "code_review": {"model": "sonnet", "reason": "Requires understanding but not complex reasoning"},
    "complex_reasoning": {"model": "opus", "reason": "Requires deep reasoning capabilities"},
    "architecture_design": {"model": "opus", "reason": "Critical decisions, needs best quality"},
    "security_analysis": {"model": "opus", "reason": "Cannot afford mistakes in security"},
}


@dataclass
class CostEstimate:
    """Cost estimate for a task."""
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation."""
    current_model: str
    recommended_model: str
    task_type: str
    estimated_savings_percent: float
    quality_impact: str
    reason: str


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> CostEstimate:
    """Calculate cost for given model and tokens."""
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model: {model}")

    pricing = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return CostEstimate(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=round(input_cost, 6),
        output_cost=round(output_cost, 6),
        total_cost=round(input_cost + output_cost, 6),
    )


def get_recommendation(task_type: str) -> OptimizationRecommendation:
    """Get model recommendation for task type."""
    if task_type not in TASK_RECOMMENDATIONS:
        # Default recommendation
        return OptimizationRecommendation(
            current_model="sonnet",
            recommended_model="sonnet",
            task_type=task_type,
            estimated_savings_percent=0,
            quality_impact="none",
            reason="Default recommendation for unknown task type",
        )

    rec = TASK_RECOMMENDATIONS[task_type]
    recommended = rec["model"]

    # Calculate savings compared to opus
    opus_cost = MODEL_PRICING["opus"]["output"]
    rec_cost = MODEL_PRICING[recommended]["output"]
    savings = round((1 - rec_cost / opus_cost) * 100, 1)

    quality_impact = "none"
    if recommended == "haiku":
        quality_impact = "minor reduction"
    elif recommended == "sonnet":
        quality_impact = "minimal"

    return OptimizationRecommendation(
        current_model="opus",
        recommended_model=recommended,
        task_type=task_type,
        estimated_savings_percent=savings,
        quality_impact=quality_impact,
        reason=rec["reason"],
    )


def analyze_usage() -> Dict:
    """Analyze usage patterns."""
    usage_data = []
    if USAGE_FILE.exists():
        for line in USAGE_FILE.read_text().splitlines():
            if line.strip():
                usage_data.append(json.loads(line))

    if not usage_data:
        # Return mock data for demonstration
        return {
            "total_requests": 0,
            "total_cost": 0,
            "by_model": {},
            "potential_savings": 0,
            "recommendations": ["No usage data available. Start tracking to get recommendations."],
        }

    by_model = {}
    total_cost = 0

    for entry in usage_data:
        model = entry.get("model", "unknown")
        cost = entry.get("cost", 0)
        
        if model not in by_model:
            by_model[model] = {"requests": 0, "cost": 0, "tokens": 0}
        
        by_model[model]["requests"] += 1
        by_model[model]["cost"] += cost
        by_model[model]["tokens"] += entry.get("tokens", 0)
        total_cost += cost

    # Calculate potential savings
    potential_savings = 0
    recommendations = []

    if "opus" in by_model and by_model["opus"]["requests"] > 10:
        # Suggest moving some opus to sonnet
        opus_cost = by_model["opus"]["cost"]
        potential_savings = opus_cost * 0.3  # Assume 30% could be sonnet
        recommendations.append(f"Consider using Sonnet for simple tasks (potential savings: ${potential_savings:.2f})")

    return {
        "total_requests": len(usage_data),
        "total_cost": round(total_cost, 4),
        "by_model": by_model,
        "potential_savings": round(potential_savings, 4),
        "recommendations": recommendations,
    }


def log_usage(model: str, input_tokens: int, output_tokens: int):
    """Log usage for analysis."""
    COST_DIR.mkdir(parents=True, exist_ok=True)
    
    cost = calculate_cost(model, input_tokens, output_tokens)
    entry = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost.total_cost,
        "tokens": input_tokens + output_tokens,
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(USAGE_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def print_cost(cost: CostEstimate):
    """Print cost estimate."""
    print(f"\n{'='*40}")
    print(f"COST ESTIMATE: {cost.model}")
    print(f"{'='*40}")
    print(f"Input Tokens: {cost.input_tokens:,}")
    print(f"Output Tokens: {cost.output_tokens:,}")
    print(f"Input Cost: ${cost.input_cost:.6f}")
    print(f"Output Cost: ${cost.output_cost:.6f}")
    print(f"Total Cost: ${cost.total_cost:.6f}")
    print(f"{'='*40}")


def print_recommendation(rec: OptimizationRecommendation):
    """Print optimization recommendation."""
    print(f"\n{'='*50}")
    print(f"RECOMMENDATION: {rec.task_type}")
    print(f"{'='*50}")
    print(f"Recommended Model: {rec.recommended_model}")
    print(f"Estimated Savings: {rec.estimated_savings_percent}%")
    print(f"Quality Impact: {rec.quality_impact}")
    print(f"Reason: {rec.reason}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="Cost Optimizer")
    parser.add_argument("--analyze", "-a", action="store_true", help="Analyze usage")
    parser.add_argument("--recommend", "-r", help="Get recommendation for task type")
    parser.add_argument("--simulate", nargs=3, metavar=("MODEL", "INPUT", "OUTPUT"), help="Simulate cost")
    parser.add_argument("--list-tasks", "-l", action="store_true", help="List task types")
    parser.add_argument("--log", nargs=3, metavar=("MODEL", "INPUT", "OUTPUT"), help="Log usage")
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()

    if args.list_tasks:
        for task, rec in TASK_RECOMMENDATIONS.items():
            print(f"📋 {task} → {rec['model']}")
        return 0

    if args.simulate:
        model, input_t, output_t = args.simulate
        try:
            cost = calculate_cost(model, int(input_t), int(output_t))
            if args.json:
                print(json.dumps(asdict(cost), indent=2))
            else:
                print_cost(cost)
        except ValueError as e:
            print(f"❌ {e}")
            return 1
        return 0

    if args.recommend:
        rec = get_recommendation(args.recommend)
        if args.json:
            print(json.dumps(asdict(rec), indent=2))
        else:
            print_recommendation(rec)
        return 0

    if args.analyze:
        analysis = analyze_usage()
        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print(f"\nTotal Requests: {analysis['total_requests']}")
            print(f"Total Cost: ${analysis['total_cost']:.4f}")
            if analysis['recommendations']:
                print("\nRecommendations:")
                for r in analysis['recommendations']:
                    print(f"  💡 {r}")
        return 0

    if args.log:
        model, input_t, output_t = args.log
        log_usage(model, int(input_t), int(output_t))
        print(f"✅ Usage logged: {model}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
