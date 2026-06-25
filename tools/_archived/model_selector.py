#!/usr/bin/env python3
"""
Model Selector Helper (GAP-CODE-MODEL-007)

Helps select optimal model for task based on requirements.
Considers: complexity, cost, speed, context length, capabilities.

Usage:
    python model_selector.py --task "code review" --priority speed
    python model_selector.py --interactive
    python model_selector.py --compare claude-sonnet gpt-4o
"""

import argparse
import json
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass

# Model database with capabilities
MODELS = {
    # Anthropic
    "claude-opus-4.5": {
        "provider": "Anthropic",
        "context": 200000,
        "cost_input": 15.0,  # per 1M tokens
        "cost_output": 75.0,
        "speed": "slow",
        "capabilities": ["complex_reasoning", "code", "analysis", "creative", "safety"],
        "best_for": ["critical_systems", "security_audit", "architecture", "complex_logic"],
        "tier": "flagship",
    },
    "claude-sonnet-4": {
        "provider": "Anthropic",
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "speed": "medium",
        "capabilities": ["code", "analysis", "general", "tool_use"],
        "best_for": ["coding", "general_tasks", "refactoring", "debugging"],
        "tier": "balanced",
    },
    "claude-haiku-3.5": {
        "provider": "Anthropic",
        "context": 200000,
        "cost_input": 0.25,
        "cost_output": 1.25,
        "speed": "fast",
        "capabilities": ["simple_tasks", "formatting", "extraction"],
        "best_for": ["simple_tasks", "data_extraction", "formatting", "quick_answers"],
        "tier": "fast",
    },
    # OpenAI
    "gpt-4o": {
        "provider": "OpenAI",
        "context": 128000,
        "cost_input": 2.5,
        "cost_output": 10.0,
        "speed": "medium",
        "capabilities": ["code", "analysis", "multimodal", "general"],
        "best_for": ["balanced_tasks", "multimodal", "general_coding"],
        "tier": "balanced",
    },
    "gpt-4o-mini": {
        "provider": "OpenAI",
        "context": 128000,
        "cost_input": 0.15,
        "cost_output": 0.60,
        "speed": "fast",
        "capabilities": ["simple_tasks", "code", "chat"],
        "best_for": ["simple_tasks", "quick_code", "chat"],
        "tier": "fast",
    },
    # Others
    "deepseek-coder-v2": {
        "provider": "DeepSeek",
        "context": 128000,
        "cost_input": 0.14,
        "cost_output": 0.28,
        "speed": "fast",
        "capabilities": ["code", "multi_language"],
        "best_for": ["high_volume_code", "cost_sensitive", "multi_language"],
        "tier": "budget",
    },
    "mistral-devstral": {
        "provider": "Mistral",
        "context": 32000,
        "cost_input": 0.1,
        "cost_output": 0.3,
        "speed": "very_fast",
        "capabilities": ["code", "agentic"],
        "best_for": ["fast_completion", "edge_deployment", "european_compliance"],
        "tier": "budget",
    },
    "codestral": {
        "provider": "Mistral",
        "context": 32000,
        "cost_input": 0.2,
        "cost_output": 0.6,
        "speed": "fast",
        "capabilities": ["code", "fill_in_middle"],
        "best_for": ["code_completion", "inline_suggestions"],
        "tier": "code_specialist",
    },
}

# Task to capability mapping
TASK_REQUIREMENTS = {
    "security_audit": {
        "required": ["complex_reasoning", "safety"],
        "preferred": ["analysis"],
        "priority_speed": False,
        "min_tier": "flagship",
    },
    "code_review": {
        "required": ["code", "analysis"],
        "preferred": ["complex_reasoning"],
        "priority_speed": False,
        "min_tier": "balanced",
    },
    "refactoring": {
        "required": ["code"],
        "preferred": ["analysis"],
        "priority_speed": False,
        "min_tier": "balanced",
    },
    "bug_fix": {
        "required": ["code"],
        "preferred": ["analysis"],
        "priority_speed": True,
        "min_tier": "balanced",
    },
    "code_generation": {
        "required": ["code"],
        "preferred": [],
        "priority_speed": True,
        "min_tier": "fast",
    },
    "data_extraction": {
        "required": ["extraction"],
        "preferred": [],
        "priority_speed": True,
        "min_tier": "fast",
    },
    "documentation": {
        "required": ["general"],
        "preferred": ["creative"],
        "priority_speed": True,
        "min_tier": "fast",
    },
    "architecture": {
        "required": ["complex_reasoning", "analysis"],
        "preferred": ["code"],
        "priority_speed": False,
        "min_tier": "flagship",
    },
    "simple_query": {
        "required": [],
        "preferred": [],
        "priority_speed": True,
        "min_tier": "fast",
    },
}


@dataclass
class ModelRecommendation:
    """Model recommendation with reasoning."""
    model: str
    score: int
    reasons: List[str]
    warnings: List[str]
    cost_estimate: str
    alternative: Optional[str] = None


def calculate_model_score(model_name: str, model: Dict, task: str, priority: str, context_needed: int = 0) -> ModelRecommendation:
    """Calculate model suitability score for task."""
    score = 50  # Base score
    reasons = []
    warnings = []

    task_req = TASK_REQUIREMENTS.get(task, {})

    # Check required capabilities
    required = task_req.get("required", [])
    for cap in required:
        if cap in model["capabilities"]:
            score += 15
            reasons.append(f"Has required capability: {cap}")
        else:
            score -= 20
            warnings.append(f"Missing required capability: {cap}")

    # Check preferred capabilities
    preferred = task_req.get("preferred", [])
    for cap in preferred:
        if cap in model["capabilities"]:
            score += 5
            reasons.append(f"Has preferred capability: {cap}")

    # Check context length
    if context_needed > 0:
        if model["context"] >= context_needed:
            score += 10
            reasons.append(f"Sufficient context: {model['context']:,} tokens")
        else:
            score -= 30
            warnings.append(f"Insufficient context: {model['context']:,} < {context_needed:,}")

    # Check speed priority
    if priority == "speed":
        if model["speed"] in ["fast", "very_fast"]:
            score += 20
            reasons.append(f"Fast speed: {model['speed']}")
        elif model["speed"] == "slow":
            score -= 10

    # Check cost priority
    if priority == "cost":
        if model["cost_input"] < 1.0:
            score += 20
            reasons.append(f"Low cost: ${model['cost_input']}/1M input")
        elif model["cost_input"] > 5.0:
            score -= 10

    # Check quality priority
    if priority == "quality":
        if model["tier"] == "flagship":
            score += 25
            reasons.append("Flagship tier for highest quality")
        elif model["tier"] == "balanced":
            score += 10

    # Check tier requirements
    min_tier = task_req.get("min_tier", "fast")
    tier_order = {"budget": 0, "fast": 1, "balanced": 2, "flagship": 3, "code_specialist": 2}
    if tier_order.get(model["tier"], 0) < tier_order.get(min_tier, 0):
        score -= 15
        warnings.append(f"Below recommended tier: {model['tier']} < {min_tier}")

    # Cost estimate (assuming 10K tokens)
    cost_est = (model["cost_input"] * 5 + model["cost_output"] * 5) / 1000
    cost_str = f"~${cost_est:.4f} per 10K tokens"

    return ModelRecommendation(
        model=model_name,
        score=min(100, max(0, score)),
        reasons=reasons,
        warnings=warnings,
        cost_estimate=cost_str,
    )


def recommend_models(task: str, priority: str = "balanced", context_needed: int = 0) -> List[ModelRecommendation]:
    """Get ranked model recommendations."""
    recommendations = []

    for model_name, model in MODELS.items():
        rec = calculate_model_score(model_name, model, task, priority, context_needed)
        recommendations.append(rec)

    # Sort by score descending
    recommendations.sort(key=lambda x: x.score, reverse=True)

    # Add alternatives
    if len(recommendations) >= 2:
        recommendations[0].alternative = recommendations[1].model

    return recommendations


def compare_models(model1: str, model2: str) -> Dict:
    """Compare two models."""
    if model1 not in MODELS or model2 not in MODELS:
        return {"error": "Model not found"}

    m1 = MODELS[model1]
    m2 = MODELS[model2]

    comparison = {
        "models": [model1, model2],
        "context": {model1: m1["context"], model2: m2["context"]},
        "cost_input": {model1: m1["cost_input"], model2: m2["cost_input"]},
        "cost_output": {model1: m1["cost_output"], model2: m2["cost_output"]},
        "speed": {model1: m1["speed"], model2: m2["speed"]},
        "tier": {model1: m1["tier"], model2: m2["tier"]},
        "capabilities": {
            model1: m1["capabilities"],
            model2: m2["capabilities"],
            "shared": list(set(m1["capabilities"]) & set(m2["capabilities"])),
            f"only_{model1}": list(set(m1["capabilities"]) - set(m2["capabilities"])),
            f"only_{model2}": list(set(m2["capabilities"]) - set(m1["capabilities"])),
        },
        "recommendation": "",
    }

    # Generate recommendation
    if m1["tier"] == "flagship" and m2["tier"] != "flagship":
        comparison["recommendation"] = f"{model1} for quality-critical tasks"
    elif m2["tier"] == "flagship" and m1["tier"] != "flagship":
        comparison["recommendation"] = f"{model2} for quality-critical tasks"
    elif m1["cost_input"] < m2["cost_input"]:
        comparison["recommendation"] = f"{model1} for cost-sensitive tasks"
    else:
        comparison["recommendation"] = f"{model2} for cost-sensitive tasks"

    return comparison


def interactive_selector():
    """Interactive model selection."""
    print("\n=== Model Selector ===\n")

    # Get task
    print("Available tasks:")
    for i, task in enumerate(TASK_REQUIREMENTS.keys(), 1):
        print(f"  {i}. {task}")
    print()

    try:
        task_choice = input("Select task number (or type custom): ").strip()
        if task_choice.isdigit():
            tasks = list(TASK_REQUIREMENTS.keys())
            task = tasks[int(task_choice) - 1]
        else:
            task = task_choice
    except Exception:
        task = "code_generation"

    # Get priority
    print("\nPriority:")
    print("  1. balanced (default)")
    print("  2. speed")
    print("  3. cost")
    print("  4. quality")

    try:
        priority_choice = input("Select priority (1-4): ").strip()
        priorities = ["balanced", "speed", "cost", "quality"]
        priority = priorities[int(priority_choice) - 1] if priority_choice.isdigit() else "balanced"
    except Exception:
        priority = "balanced"

    # Get context
    try:
        context = int(input("\nContext tokens needed (0 for default): ").strip() or "0")
    except Exception:
        context = 0

    # Get recommendations
    recs = recommend_models(task, priority, context)
    print_recommendations(recs, task, priority)


def print_recommendations(recommendations: List[ModelRecommendation], task: str, priority: str):
    """Print recommendations."""
    print("\n" + "="*60)
    print("MODEL RECOMMENDATIONS")
    print("="*60)
    print(f"\nTask: {task}")
    print(f"Priority: {priority}")
    print()

    for i, rec in enumerate(recommendations[:5], 1):
        print(f"{i}. {rec.model} (Score: {rec.score}/100)")
        print(f"   Cost: {rec.cost_estimate}")
        if rec.reasons:
            print(f"   ✅ {', '.join(rec.reasons[:3])}")
        if rec.warnings:
            print(f"   ⚠️  {', '.join(rec.warnings[:2])}")
        if rec.alternative:
            print(f"   Alternative: {rec.alternative}")
        print()

    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Model Selector Helper")
    parser.add_argument("--task", "-t", help="Task type")
    parser.add_argument("--priority", "-p", choices=["balanced", "speed", "cost", "quality"], default="balanced")
    parser.add_argument("--context", "-c", type=int, default=0, help="Context tokens needed")
    parser.add_argument("--compare", nargs=2, metavar=("MODEL1", "MODEL2"), help="Compare two models")
    parser.add_argument("--list-tasks", action="store_true", help="List available tasks")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.list_tasks:
        print("\nAvailable tasks:")
        for task, req in TASK_REQUIREMENTS.items():
            print(f"  {task}")
            print(f"    Required: {req.get('required', [])}")
            print(f"    Min tier: {req.get('min_tier', 'fast')}")
        return 0

    if args.list_models:
        print("\nAvailable models:")
        for name, model in MODELS.items():
            print(f"  {name} [{model['provider']}]")
            print(f"    Tier: {model['tier']}, Speed: {model['speed']}")
            print(f"    Cost: ${model['cost_input']}/{model['cost_output']} per 1M tokens")
            print(f"    Context: {model['context']:,}")
        return 0

    if args.interactive:
        interactive_selector()
        return 0

    if args.compare:
        result = compare_models(args.compare[0], args.compare[1])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "="*60)
            print("MODEL COMPARISON")
            print("="*60)
            for key, val in result.items():
                print(f"{key}: {val}")
        return 0

    if args.task:
        recommendations = recommend_models(args.task, args.priority, args.context)
        if args.json:
            print(json.dumps([{
                "model": r.model,
                "score": r.score,
                "reasons": r.reasons,
                "warnings": r.warnings,
                "cost": r.cost_estimate,
            } for r in recommendations], indent=2))
        else:
            print_recommendations(recommendations, args.task, args.priority)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
