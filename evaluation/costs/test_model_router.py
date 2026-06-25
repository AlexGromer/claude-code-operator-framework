#!/usr/bin/env python3
"""
Test suite for Model Router.

Task 23: Model Selection Optimization (GAP-COST-MODEL)
Tests complexity classification, model routing, cost estimation,
and override behavior.

Version: 1.0.0
Date: 2026-02-03
"""

import pytest
from model_router import (
    ModelRouter,
    TaskComplexity,
    ModelType,
    RoutingDecision,
)


class TestTaskComplexityEnum:
    """Tests for TaskComplexity enum."""

    def test_complexity_values(self):
        """Verify complexity level values."""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.COMPLEX.value == "complex"

    def test_all_levels_exist(self):
        """All three complexity levels exist."""
        levels = list(TaskComplexity)
        assert len(levels) == 3


class TestModelTypeEnum:
    """Tests for ModelType enum."""

    def test_model_values(self):
        """Verify model type values."""
        assert ModelType.HAIKU.value == "haiku"
        assert ModelType.SONNET.value == "sonnet"
        assert ModelType.OPUS.value == "opus"

    def test_all_models_exist(self):
        """All three model types exist."""
        models = list(ModelType)
        assert len(models) == 3


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_create_basic_decision(self):
        """Create a basic routing decision."""
        decision = RoutingDecision(
            model=ModelType.SONNET,
            complexity=TaskComplexity.MEDIUM,
            confidence=0.8,
            reasoning="Test reasoning",
            keywords_matched=["analyze"],
        )
        assert decision.model == ModelType.SONNET
        assert decision.complexity == TaskComplexity.MEDIUM
        assert decision.confidence == 0.8
        assert decision.override_reason is None

    def test_create_decision_with_override(self):
        """Create decision with override reason."""
        decision = RoutingDecision(
            model=ModelType.OPUS,
            complexity=TaskComplexity.SIMPLE,
            confidence=0.5,
            reasoning="Override test",
            keywords_matched=[],
            override_reason="Quality override: critical",
        )
        assert decision.override_reason == "Quality override: critical"


class TestModelRouterInit:
    """Tests for ModelRouter initialization."""

    def test_default_init(self):
        """Default initialization uses default routing rules."""
        router = ModelRouter()
        assert router.routing_rules == ModelRouter.DEFAULT_ROUTING_RULES

    def test_custom_routing_rules(self):
        """Custom routing rules are applied."""
        custom_rules = {
            TaskComplexity.SIMPLE: ModelType.HAIKU,
            TaskComplexity.MEDIUM: ModelType.HAIKU,
            TaskComplexity.COMPLEX: ModelType.OPUS,
        }
        router = ModelRouter(routing_rules=custom_rules)
        assert router.routing_rules == custom_rules


class TestComplexityClassification:
    """Tests for complexity classification."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_simple_task_list(self, router):
        """List operation is classified as simple."""
        complexity, confidence, keywords = router.classify_complexity(
            "List all files in the current directory"
        )
        assert complexity == TaskComplexity.SIMPLE
        assert "list" in keywords

    def test_simple_task_show(self, router):
        """Show operation is classified as simple."""
        complexity, confidence, keywords = router.classify_complexity(
            "Show git status"
        )
        assert complexity == TaskComplexity.SIMPLE
        assert "show" in keywords or "status" in keywords

    def test_simple_task_get(self, router):
        """Get operation is classified as simple."""
        complexity, confidence, keywords = router.classify_complexity(
            "Get the current version"
        )
        assert complexity == TaskComplexity.SIMPLE
        assert "get" in keywords or "version" in keywords

    def test_medium_task_analyze(self, router):
        """Analyze operation is classified as medium."""
        complexity, confidence, keywords = router.classify_complexity(
            "Analyze code for security vulnerabilities"
        )
        assert complexity == TaskComplexity.MEDIUM
        assert "analyze" in keywords

    def test_medium_task_refactor(self, router):
        """Refactor operation is classified as medium."""
        complexity, confidence, keywords = router.classify_complexity(
            "Refactor the authentication module"
        )
        assert complexity == TaskComplexity.MEDIUM
        assert "refactor" in keywords

    def test_medium_task_review(self, router):
        """Review operation is classified as medium."""
        complexity, confidence, keywords = router.classify_complexity(
            "Review pull request changes"
        )
        assert complexity == TaskComplexity.MEDIUM
        assert "review" in keywords

    def test_complex_task_design(self, router):
        """Design operation is classified as complex."""
        complexity, confidence, keywords = router.classify_complexity(
            "Design microservices architecture"
        )
        assert complexity == TaskComplexity.COMPLEX
        assert "design" in keywords

    def test_complex_task_implement(self, router):
        """Implement operation is classified as complex."""
        complexity, confidence, keywords = router.classify_complexity(
            "Implement OAuth2 integration"
        )
        assert complexity == TaskComplexity.COMPLEX
        assert "implement" in keywords

    def test_complex_task_architect(self, router):
        """Architect operation is classified as complex."""
        complexity, confidence, keywords = router.classify_complexity(
            "Architect the data pipeline for analytics"
        )
        assert complexity == TaskComplexity.COMPLEX
        assert "architect" in keywords

    def test_no_keywords_defaults_to_medium(self, router):
        """Unknown task defaults to medium complexity."""
        complexity, confidence, keywords = router.classify_complexity(
            "Random task with no keywords"
        )
        assert complexity == TaskComplexity.MEDIUM
        assert confidence == 0.3
        assert keywords == []

    def test_confidence_calculation(self, router):
        """Confidence is calculated correctly."""
        # Task with clear keywords
        complexity, confidence, keywords = router.classify_complexity(
            "List and show files"
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.3  # More confident than default

    def test_multiple_keywords_matched(self, router):
        """Multiple matching keywords increases confidence."""
        complexity, confidence, keywords = router.classify_complexity(
            "List, show, and check all files"
        )
        assert len(keywords) >= 2
        assert confidence > 0.5


class TestModelSelection:
    """Tests for model selection."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_simple_task_routes_to_haiku(self, router):
        """Simple task routes to Haiku."""
        decision = router.select_model("List all files")
        assert decision.model == ModelType.HAIKU
        assert decision.complexity == TaskComplexity.SIMPLE

    def test_medium_task_routes_to_sonnet(self, router):
        """Medium task routes to Sonnet."""
        decision = router.select_model("Analyze code quality")
        assert decision.model == ModelType.SONNET
        assert decision.complexity == TaskComplexity.MEDIUM

    def test_complex_task_routes_to_sonnet_by_default(self, router):
        """Complex task routes to Sonnet by default (not Opus)."""
        decision = router.select_model("Design API architecture")
        assert decision.model == ModelType.SONNET
        assert decision.complexity == TaskComplexity.COMPLEX


class TestQualityOverrides:
    """Tests for quality preference overrides."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_critical_quality_selects_opus(self, router):
        """Critical quality forces Opus selection."""
        decision = router.select_model("List files", quality="critical")
        assert decision.model == ModelType.OPUS
        assert "Quality override" in decision.override_reason

    def test_low_quality_selects_haiku(self, router):
        """Low quality forces Haiku selection."""
        decision = router.select_model("Design system", quality="low")
        assert decision.model == ModelType.HAIKU
        assert "Quality override" in decision.override_reason

    def test_balanced_uses_routing_rules(self, router):
        """Balanced quality uses default routing rules."""
        decision = router.select_model("Analyze code", quality="balanced")
        assert decision.model == ModelType.SONNET
        assert decision.override_reason is None


class TestBudgetConstraints:
    """Tests for budget constraint handling."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_low_budget_forces_haiku(self, router):
        """Budget < $0.01 forces Haiku."""
        decision = router.select_model("Design architecture", budget=0.005)
        assert decision.model == ModelType.HAIKU
        assert "Budget override" in decision.override_reason

    def test_adequate_budget_uses_routing(self, router):
        """Budget >= $0.01 allows normal routing."""
        decision = router.select_model("Analyze code", budget=0.05)
        assert decision.model == ModelType.SONNET
        assert decision.override_reason is None

    def test_no_budget_allows_routing(self, router):
        """No budget constraint uses routing rules."""
        decision = router.select_model("Design system", budget=None)
        assert decision.override_reason is None


class TestExplicitOverride:
    """Tests for explicit model override."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_override_haiku(self, router):
        """Explicit override to Haiku."""
        decision = router.select_model("Design", override_model="haiku")
        assert decision.model == ModelType.HAIKU
        assert "User specified model" in decision.override_reason

    def test_override_sonnet(self, router):
        """Explicit override to Sonnet."""
        decision = router.select_model("List files", override_model="sonnet")
        assert decision.model == ModelType.SONNET
        assert "User specified model" in decision.override_reason

    def test_override_opus(self, router):
        """Explicit override to Opus."""
        decision = router.select_model("List files", override_model="opus")
        assert decision.model == ModelType.OPUS
        assert "User specified model" in decision.override_reason

    def test_override_confidence_is_1(self, router):
        """Override sets confidence to 1.0."""
        decision = router.select_model("Any task", override_model="opus")
        assert decision.confidence == 1.0


class TestCostSavingsEstimation:
    """Tests for cost savings estimation."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_simple_task_savings(self, router):
        """Simple task shows savings vs Sonnet baseline."""
        result = router.estimate_cost_savings("List all files")
        assert result["routed_model"] == "haiku"
        assert result["baseline_model"] == "sonnet"
        assert result["savings"] > 0
        assert result["savings_pct"] > 0

    def test_medium_task_no_savings(self, router):
        """Medium task has no savings against Sonnet baseline."""
        result = router.estimate_cost_savings("Analyze code quality")
        assert result["routed_model"] == "sonnet"
        assert result["savings"] == 0

    def test_estimated_tokens_based_on_complexity(self, router):
        """Estimated tokens vary by complexity."""
        simple_result = router.estimate_cost_savings("List files")
        complex_result = router.estimate_cost_savings("Design architecture")

        assert simple_result["estimated_tokens"] < complex_result["estimated_tokens"]

    def test_custom_baseline(self, router):
        """Custom baseline model for comparison."""
        result = router.estimate_cost_savings(
            "List files",
            baseline_model=ModelType.OPUS
        )
        assert result["baseline_model"] == "opus"
        assert result["savings_pct"] > 90  # Haiku vs Opus = major savings


class TestFormattedOutput:
    """Tests for formatted output."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_format_contains_model(self, router):
        """Formatted output contains model name."""
        decision = router.select_model("List files")
        formatted = router.format_routing_decision(decision)
        assert "haiku" in formatted.lower()

    def test_format_contains_complexity(self, router):
        """Formatted output contains complexity."""
        decision = router.select_model("Analyze code")
        formatted = router.format_routing_decision(decision)
        assert "medium" in formatted.lower()

    def test_format_contains_override_reason(self, router):
        """Formatted output contains override reason when present."""
        decision = router.select_model("List", quality="critical")
        formatted = router.format_routing_decision(decision)
        assert "Override" in formatted


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_empty_task_description(self, router):
        """Empty task description defaults to medium."""
        complexity, confidence, keywords = router.classify_complexity("")
        assert complexity == TaskComplexity.MEDIUM
        assert confidence == 0.3

    def test_very_long_task_description(self, router):
        """Very long task description is handled."""
        long_task = "list " * 1000 + "design architecture"
        decision = router.select_model(long_task)
        # Should still work without error
        assert decision.model in list(ModelType)

    def test_case_insensitive_matching(self, router):
        """Keyword matching is case-insensitive."""
        upper_decision = router.select_model("LIST ALL FILES")
        lower_decision = router.select_model("list all files")
        assert upper_decision.complexity == lower_decision.complexity

    def test_word_boundary_matching(self, router):
        """Keywords match on word boundaries only."""
        # "listing" should not match "list"
        complexity, _, keywords = router.classify_complexity("listing items")
        # "list" should NOT be in keywords (word boundary prevents match)
        assert "list" not in keywords


class TestRoutingAccuracy:
    """Tests for routing accuracy metrics."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_routing_accuracy_simple_tasks(self, router):
        """Routing accuracy for simple tasks."""
        simple_tasks = [
            "list files",
            "show status",
            "get version",
            "check health",
            "find config",
        ]
        correct = sum(
            1 for task in simple_tasks
            if router.select_model(task).complexity == TaskComplexity.SIMPLE
        )
        accuracy = correct / len(simple_tasks)
        assert accuracy >= 0.8  # 80% accuracy threshold

    def test_routing_accuracy_medium_tasks(self, router):
        """Routing accuracy for medium tasks."""
        medium_tasks = [
            "analyze code",
            "review changes",
            "refactor module",
            "debug error",
            "test feature",
        ]
        correct = sum(
            1 for task in medium_tasks
            if router.select_model(task).complexity == TaskComplexity.MEDIUM
        )
        accuracy = correct / len(medium_tasks)
        assert accuracy >= 0.8  # 80% accuracy threshold

    def test_routing_accuracy_complex_tasks(self, router):
        """Routing accuracy for complex tasks."""
        complex_tasks = [
            "design architecture",
            "implement feature",
            "create module",
            "build system",
            "migrate database",
        ]
        correct = sum(
            1 for task in complex_tasks
            if router.select_model(task).complexity == TaskComplexity.COMPLEX
        )
        accuracy = correct / len(complex_tasks)
        assert accuracy >= 0.8  # 80% accuracy threshold


class TestIntegration:
    """Integration tests."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ModelRouter()

    def test_full_workflow_simple(self, router):
        """Full workflow for simple task."""
        task = "List all Python files in src directory"

        # Classify
        complexity, confidence, keywords = router.classify_complexity(task)
        assert complexity == TaskComplexity.SIMPLE

        # Route
        decision = router.select_model(task)
        assert decision.model == ModelType.HAIKU

        # Cost analysis
        cost = router.estimate_cost_savings(task)
        assert cost["savings_pct"] > 0

    def test_full_workflow_with_quality_override(self, router):
        """Full workflow with quality override."""
        task = "List files"

        # Override to critical
        decision = router.select_model(task, quality="critical")
        assert decision.model == ModelType.OPUS
        assert decision.complexity == TaskComplexity.SIMPLE  # Still simple

        # Cost analysis shows negative savings (Opus more expensive)
        cost = router.estimate_cost_savings(task)
        # Baseline Sonnet vs actual routing (Haiku without override)
        assert cost["routed_model"] == "haiku"  # Without override

    def test_decision_object_is_complete(self, router):
        """RoutingDecision object has all required fields."""
        decision = router.select_model("Analyze security vulnerabilities")

        # All fields populated
        assert decision.model is not None
        assert decision.complexity is not None
        assert 0.0 <= decision.confidence <= 1.0
        assert decision.reasoning is not None
        assert isinstance(decision.keywords_matched, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
