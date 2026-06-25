#!/usr/bin/env python3
"""
Model Router for Task Tool
TIER 2B Task 18: GAP-COST-IMPL-002

Automatically selects optimal Claude model (haiku/sonnet/opus) based on task complexity.
Implements keyword-based classification with quality/budget override support.

Target: -75% cost reduction on mixed workload via strategic model routing
ROI: Haiku for simple tasks, Sonnet for balanced, Opus for critical design work
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"       # List, show, get, read operations
    MEDIUM = "medium"       # Analyze, review, refactor operations
    COMPLEX = "complex"     # Design, architect, create, implement operations


class ModelType(Enum):
    """Available Claude models."""
    HAIKU = "haiku"         # Fast, cheap, simple tasks
    SONNET = "sonnet"       # Balanced, default
    OPUS = "opus"           # Powerful, complex tasks


@dataclass
class RoutingDecision:
    """Represents a model routing decision with rationale."""
    model: ModelType
    complexity: TaskComplexity
    confidence: float  # 0.0-1.0
    reasoning: str
    keywords_matched: List[str]
    override_reason: Optional[str] = None


class ModelRouter:
    """
    Routes Task tool invocations to appropriate Claude model.

    TIER 2B Task 18 (GAP-COST-IMPL-002): Model Router for Task Tool
    - Complexity classification via keyword matching
    - Quality/budget override support
    - Detailed routing decision logging
    """

    # Keyword patterns for complexity classification
    COMPLEXITY_KEYWORDS = {
        TaskComplexity.SIMPLE: [
            # Read operations
            "list", "show", "get", "read", "display", "view", "check",
            "find", "search", "grep", "glob", "cat", "ls",

            # Simple queries
            "what is", "where is", "which", "when",

            # Status checks
            "status", "health", "info", "version",

            # Simple modifications
            "add line", "remove line", "rename", "move",
        ],

        TaskComplexity.MEDIUM: [
            # Analysis operations
            "analyze", "review", "investigate", "inspect", "examine",
            "evaluate", "assess", "compare", "validate",

            # Code modifications
            "refactor", "optimize", "improve", "enhance", "update",
            "fix", "debug", "troubleshoot",

            # Documentation
            "document", "explain", "describe", "summarize",

            # Testing
            "test", "verify", "validate", "benchmark",
        ],

        TaskComplexity.COMPLEX: [
            # Architecture & Design
            "design", "architect", "plan", "strategy", "approach",
            "framework", "system design", "infrastructure",

            # Implementation
            "implement", "create", "build", "develop", "write",
            "generate", "construct",

            # Multi-step operations
            "migrate", "transform", "convert", "integrate",
            "deploy", "orchestrate",

            # Research & exploration
            "research", "explore", "discover", "prototype",
        ],
    }

    # Default routing rules (complexity → model)
    DEFAULT_ROUTING_RULES = {
        TaskComplexity.SIMPLE: ModelType.HAIKU,
        TaskComplexity.MEDIUM: ModelType.SONNET,
        TaskComplexity.COMPLEX: ModelType.SONNET,  # Default to Sonnet, not Opus
    }

    # Token estimate thresholds (approximate)
    TOKEN_THRESHOLDS = {
        "simple": 5000,      # <5k tokens
        "medium": 20000,     # 5k-20k tokens
        "complex": 100000,   # >20k tokens
    }

    def __init__(self, routing_rules: Optional[Dict[TaskComplexity, ModelType]] = None):
        """
        Initialize model router.

        Args:
            routing_rules: Custom routing rules (complexity → model)
        """
        self.routing_rules = routing_rules or self.DEFAULT_ROUTING_RULES

    def classify_complexity(self, task_description: str) -> Tuple[TaskComplexity, float, List[str]]:
        """
        Classify task complexity based on keyword matching.

        Args:
            task_description: Task description text

        Returns:
            Tuple of (complexity, confidence, matched_keywords)
        """
        task_lower = task_description.lower()

        # Score each complexity level
        scores = {
            TaskComplexity.SIMPLE: 0.0,
            TaskComplexity.MEDIUM: 0.0,
            TaskComplexity.COMPLEX: 0.0,
        }

        matched_keywords = {
            TaskComplexity.SIMPLE: [],
            TaskComplexity.MEDIUM: [],
            TaskComplexity.COMPLEX: [],
        }

        # Count keyword matches
        for complexity, keywords in self.COMPLEXITY_KEYWORDS.items():
            for keyword in keywords:
                # Use word boundary matching to avoid substring matches
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, task_lower):
                    scores[complexity] += 1.0
                    matched_keywords[complexity].append(keyword)

        # Determine complexity (highest score wins)
        if all(score == 0.0 for score in scores.values()):
            # No keywords matched → default to MEDIUM
            return TaskComplexity.MEDIUM, 0.3, []

        max_complexity = max(scores, key=scores.get)
        max_score = scores[max_complexity]
        total_score = sum(scores.values())

        # Confidence = (max_score / total_score)
        confidence = max_score / total_score if total_score > 0 else 0.5

        return max_complexity, confidence, matched_keywords[max_complexity]

    def select_model(
        self,
        task_description: str,
        quality: str = "balanced",
        budget: Optional[float] = None,
        override_model: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Select optimal model for task execution.

        Args:
            task_description: Task description text
            quality: Quality preference ("low", "balanced", "critical")
            budget: Budget constraint in USD (if specified, forces haiku if <$0.01)
            override_model: Explicit model override (bypasses routing)

        Returns:
            RoutingDecision with model, complexity, confidence, reasoning
        """
        # Handle explicit override
        if override_model:
            model = ModelType(override_model)
            return RoutingDecision(
                model=model,
                complexity=TaskComplexity.MEDIUM,  # Placeholder
                confidence=1.0,
                reasoning="Explicit model override",
                keywords_matched=[],
                override_reason=f"User specified model: {override_model}"
            )

        # Classify complexity
        complexity, confidence, keywords_matched = self.classify_complexity(task_description)

        # Apply budget constraint (strict override)
        if budget is not None and budget < 0.01:
            return RoutingDecision(
                model=ModelType.HAIKU,
                complexity=complexity,
                confidence=confidence,
                reasoning=f"Budget constraint: ${budget:.4f} < $0.01",
                keywords_matched=keywords_matched,
                override_reason=f"Budget override: ${budget:.4f} < $0.01 threshold"
            )

        # Apply quality preference
        if quality == "critical":
            return RoutingDecision(
                model=ModelType.OPUS,
                complexity=complexity,
                confidence=confidence,
                reasoning="Quality preference: critical (Opus selected)",
                keywords_matched=keywords_matched,
                override_reason="Quality override: critical → Opus"
            )

        elif quality == "low":
            return RoutingDecision(
                model=ModelType.HAIKU,
                complexity=complexity,
                confidence=confidence,
                reasoning="Quality preference: low (Haiku selected)",
                keywords_matched=keywords_matched,
                override_reason="Quality override: low → Haiku"
            )

        # Apply routing rules (default: balanced quality)
        model = self.routing_rules[complexity]

        reasoning = (
            f"Complexity: {complexity.value} (confidence: {confidence:.0%}), "
            f"Keywords: {', '.join(keywords_matched[:3])}{'...' if len(keywords_matched) > 3 else ''}"
        )

        return RoutingDecision(
            model=model,
            complexity=complexity,
            confidence=confidence,
            reasoning=reasoning,
            keywords_matched=keywords_matched
        )

    def format_routing_decision(self, decision: RoutingDecision) -> str:
        """
        Format routing decision for logging/display.

        Args:
            decision: RoutingDecision object

        Returns:
            Formatted string
        """
        lines = [
            f"📊 Model Routing Decision:",
            f"  Model: {decision.model.value}",
            f"  Complexity: {decision.complexity.value} (confidence: {decision.confidence:.0%})",
            f"  Reasoning: {decision.reasoning}",
        ]

        if decision.keywords_matched:
            lines.append(f"  Keywords: {', '.join(decision.keywords_matched[:5])}")

        if decision.override_reason:
            lines.append(f"  Override: {decision.override_reason}")

        return "\n".join(lines)

    def estimate_cost_savings(
        self,
        task_description: str,
        baseline_model: ModelType = ModelType.SONNET,
    ) -> Dict[str, Any]:
        """
        Estimate cost savings from routing vs baseline.

        Args:
            task_description: Task description
            baseline_model: Baseline model (default: Sonnet)

        Returns:
            Dictionary with cost analysis
        """
        # Model cost per 1M input tokens (approximate)
        COST_PER_1M_TOKENS = {
            ModelType.HAIKU: 3.00,     # $3/1M input
            ModelType.SONNET: 30.00,   # $30/1M input
            ModelType.OPUS: 150.00,    # $150/1M input
        }

        decision = self.select_model(task_description)
        complexity = decision.complexity

        # Estimate tokens for complexity level
        estimated_tokens = {
            TaskComplexity.SIMPLE: self.TOKEN_THRESHOLDS["simple"],
            TaskComplexity.MEDIUM: self.TOKEN_THRESHOLDS["medium"],
            TaskComplexity.COMPLEX: self.TOKEN_THRESHOLDS["complex"],
        }[complexity]

        # Calculate costs
        baseline_cost = (estimated_tokens / 1_000_000) * COST_PER_1M_TOKENS[baseline_model]
        routed_cost = (estimated_tokens / 1_000_000) * COST_PER_1M_TOKENS[decision.model]

        savings = baseline_cost - routed_cost
        savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        return {
            "routed_model": decision.model.value,
            "baseline_model": baseline_model.value,
            "estimated_tokens": estimated_tokens,
            "baseline_cost": baseline_cost,
            "routed_cost": routed_cost,
            "savings": savings,
            "savings_pct": savings_pct,
            "complexity": complexity.value,
        }


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Model Router for Task Tool")
    parser.add_argument('task_description', nargs='?', help="Task description to classify")
    parser.add_argument('--quality', choices=['low', 'balanced', 'critical'], default='balanced',
                       help="Quality preference (default: balanced)")
    parser.add_argument('--budget', type=float, help="Budget constraint in USD")
    parser.add_argument('--test', action='store_true', help="Run test suite")

    args = parser.parse_args()

    router = ModelRouter()

    if args.test:
        # Test suite
        test_cases = [
            ("List all files in directory", TaskComplexity.SIMPLE, ModelType.HAIKU),
            ("Analyze code for security vulnerabilities", TaskComplexity.MEDIUM, ModelType.SONNET),
            ("Design microservices architecture for e-commerce platform", TaskComplexity.COMPLEX, ModelType.SONNET),
            ("Show git status", TaskComplexity.SIMPLE, ModelType.HAIKU),
            ("Refactor authentication module", TaskComplexity.MEDIUM, ModelType.SONNET),
            ("Implement OAuth2 integration", TaskComplexity.COMPLEX, ModelType.SONNET),
        ]

        print("=" * 70)
        print("MODEL ROUTER TEST SUITE")
        print("=" * 70)
        print()

        for task_desc, expected_complexity, expected_model in test_cases:
            decision = router.select_model(task_desc, quality=args.quality, budget=args.budget)

            print(f"Task: \"{task_desc}\"")
            print(router.format_routing_decision(decision))

            # Validation
            status = "✅" if decision.model == expected_model else "⚠️"
            print(f"{status} Expected: {expected_model.value}, Got: {decision.model.value}")

            # Cost analysis
            cost_analysis = router.estimate_cost_savings(task_desc)
            print(f"  Cost Savings: {cost_analysis['savings_pct']:+.1f}% (${cost_analysis['savings']:.4f})")
            print()

        print("=" * 70)

    elif args.task_description:
        # Single task routing
        decision = router.select_model(
            args.task_description,
            quality=args.quality,
            budget=args.budget
        )

        print(router.format_routing_decision(decision))
        print()

        # Cost analysis
        cost_analysis = router.estimate_cost_savings(args.task_description)
        print(f"💰 Cost Analysis:")
        print(f"  Estimated Tokens: {cost_analysis['estimated_tokens']:,}")
        print(f"  Routed Cost: ${cost_analysis['routed_cost']:.4f}")
        print(f"  Baseline Cost: ${cost_analysis['baseline_cost']:.4f} ({cost_analysis['baseline_model']})")
        print(f"  Savings: {cost_analysis['savings_pct']:+.1f}% (${cost_analysis['savings']:.4f})")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
