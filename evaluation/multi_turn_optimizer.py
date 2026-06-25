#!/usr/bin/env python3
"""
Multi-Turn Conversation Optimizer
TIER 3 Phase 4 Task 28: GAP-COST-AG-007

Optimizes long conversations to reduce context costs:
- Checkpoint summarization
- Reference-based replies
- Selective history retention
- Context budget management

Target: -50% cost on conversations >20 turns
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib


@dataclass
class MessageSummary:
    """Summary of a conversation segment."""
    start_turn: int
    end_turn: int
    summary_text: str
    key_decisions: List[str] = field(default_factory=list)
    key_artifacts: List[str] = field(default_factory=list)  # Files, functions, etc.
    token_count_original: int = 0
    token_count_summary: int = 0
    compression_ratio: float = 0.0


@dataclass
class ConversationCheckpoint:
    """Checkpoint in conversation for context management."""
    checkpoint_id: str
    turn_number: int
    timestamp: str
    summary: MessageSummary
    retained_context: List[str]  # Critical context to retain verbatim
    can_be_dropped: bool = True  # Whether this checkpoint can be dropped if needed


@dataclass
class HistoryRetentionPolicy:
    """Policy for what history to retain."""
    # Recent messages always kept
    recent_turns_to_keep: int = 10

    # Priority categories (higher = more likely to retain)
    priority_weights: Dict[str, float] = field(default_factory=lambda: {
        "code_artifacts": 1.0,    # Code blocks, file paths
        "decisions": 0.9,        # Key decisions made
        "errors": 0.8,           # Error messages (for debugging)
        "user_requirements": 0.7, # Original requirements
        "explanations": 0.3,     # Detailed explanations (can summarize)
        "greetings": 0.0,        # Pleasantries (can drop)
    })

    # Size thresholds
    max_history_tokens: int = 50000
    summarization_threshold: int = 30000
    aggressive_threshold: int = 70000


@dataclass
class OptimizationResult:
    """Result of conversation optimization."""
    session_id: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    savings_percentage: float
    checkpoints_created: int
    messages_summarized: int
    messages_dropped: int
    retained_categories: Dict[str, int] = field(default_factory=dict)
    strategy_used: str = "normal"  # "normal" | "aggressive" | "checkpoint"


@dataclass
class CostAnalysis:
    """Cost analysis for conversation optimization."""
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_original: float
    estimated_cost_optimized: float
    savings: float
    roi_percentage: float


class MultiTurnOptimizer:
    """
    Optimizes multi-turn conversations for cost efficiency.

    TIER 3 Phase 4 Task 28 (GAP-COST-AG-007): Multi-turn conversation optimization

    Strategies:
    1. Checkpoint summarization: Periodically summarize history
    2. Reference-based replies: Use references instead of repeating context
    3. Selective history: Retain high-value content, drop low-value
    4. Context budget: Stay within token limits
    """

    # Token estimation (rough: 1 word ≈ 1.3 tokens)
    TOKENS_PER_WORD = 1.3

    # Cost per million tokens (Claude Sonnet 4.5 pricing)
    COST_PER_M_INPUT = 3.0  # $3/M input tokens
    COST_PER_M_OUTPUT = 15.0  # $15/M output tokens

    # Content patterns for categorization
    PATTERNS = {
        "code_artifacts": [
            r'```[\s\S]*?```',  # Code blocks
            r'`[^`]+`',  # Inline code
            r'(?:def|class|function|const|let|var)\s+\w+',  # Function/class definitions
            r'/[\w/.-]+\.\w+',  # File paths
        ],
        "decisions": [
            r'\b(?:decided|decision|chose|choosing|selected|approach|strategy)\b',
            r'\b(?:will|should|must|need to)\s+\w+',
            r'(?:✅|✓|→|==>)',  # Decision markers
        ],
        "errors": [
            r'\b(?:error|exception|failed|failure|traceback)\b',
            r'\b(?:bug|issue|problem|wrong)\b',
            r'(?:❌|✗|⚠️)',  # Error markers
        ],
        "user_requirements": [
            r'\b(?:I want|I need|please|could you|can you)\b',
            r'\b(?:requirement|feature|implement|create|build)\b',
        ],
        "explanations": [
            r'\b(?:because|since|therefore|thus|hence|so that)\b',
            r'\b(?:this means|this is|that is|in other words)\b',
            r'\b(?:explanation|reason|why|how)\b',
        ],
        "greetings": [
            r'\b(?:hello|hi|hey|thanks|thank you|bye|goodbye)\b',
            r'\b(?:sure|okay|ok|got it|understood)\b',
        ],
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize optimizer."""
        self.data_dir = data_dir or Path.home() / ".claude" / "evaluation" / "data"
        self.checkpoints_file = self.data_dir / "conversation_checkpoints.jsonl"
        self.optimizations_file = self.data_dir / "optimization_results.jsonl"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.policy = HistoryRetentionPolicy()

    def optimize_conversation(
        self,
        messages: List[Dict[str, Any]],
        session_id: str = "unknown",
        force_aggressive: bool = False,
    ) -> Tuple[List[Dict[str, Any]], OptimizationResult]:
        """
        Optimize a conversation for reduced token usage.

        Args:
            messages: List of conversation messages
            session_id: Session identifier
            force_aggressive: Force aggressive optimization

        Returns:
            Tuple of (optimized messages, optimization result)
        """
        if len(messages) < 10:
            # Too short to optimize meaningfully
            return messages, self._no_optimization_result(session_id, messages)

        # Analyze current state
        original_tokens = self._estimate_tokens(messages)
        current_tokens = original_tokens

        # Determine strategy
        strategy = self._select_strategy(current_tokens, force_aggressive)

        # Apply optimization
        if strategy == "checkpoint":
            optimized, result = self._apply_checkpoint_strategy(messages, session_id)
        elif strategy == "aggressive":
            optimized, result = self._apply_aggressive_strategy(messages, session_id)
        else:
            optimized, result = self._apply_normal_strategy(messages, session_id)

        # Save result
        self._save_result(result)

        return optimized, result

    def _select_strategy(self, current_tokens: int, force_aggressive: bool) -> str:
        """Select optimization strategy based on context size."""
        if force_aggressive or current_tokens > self.policy.aggressive_threshold:
            return "aggressive"
        elif current_tokens > self.policy.summarization_threshold:
            return "checkpoint"
        else:
            return "normal"

    def _apply_normal_strategy(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
    ) -> Tuple[List[Dict[str, Any]], OptimizationResult]:
        """Normal optimization: selective retention only."""
        original_tokens = self._estimate_tokens(messages)

        # Categorize messages
        categorized = self._categorize_messages(messages)

        # Retain based on priority
        retained = []
        dropped_count = 0
        retained_categories: Dict[str, int] = defaultdict(int)

        # Always keep recent messages
        recent_start = max(0, len(messages) - self.policy.recent_turns_to_keep)

        for i, msg in enumerate(messages):
            # Always keep recent messages
            if i >= recent_start:
                retained.append(msg)
                continue

            # Check category priority
            category = categorized.get(i, "explanations")
            priority = self.policy.priority_weights.get(category, 0.3)

            if priority >= 0.5:  # Keep if priority >= 0.5
                retained.append(msg)
                retained_categories[category] += 1
            else:
                dropped_count += 1

        optimized_tokens = self._estimate_tokens(retained)

        result = OptimizationResult(
            session_id=session_id,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            tokens_saved=original_tokens - optimized_tokens,
            savings_percentage=(original_tokens - optimized_tokens) / original_tokens * 100
                              if original_tokens > 0 else 0,
            checkpoints_created=0,
            messages_summarized=0,
            messages_dropped=dropped_count,
            retained_categories=dict(retained_categories),
            strategy_used="normal",
        )

        return retained, result

    def _apply_checkpoint_strategy(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
    ) -> Tuple[List[Dict[str, Any]], OptimizationResult]:
        """Checkpoint strategy: summarize older segments."""
        original_tokens = self._estimate_tokens(messages)

        # Keep recent messages as-is
        recent_start = max(0, len(messages) - self.policy.recent_turns_to_keep)
        recent_messages = messages[recent_start:]

        # Summarize older messages in chunks
        older_messages = messages[:recent_start]
        chunk_size = 20  # Summarize 20 messages at a time
        summaries = []
        checkpoints_created = 0

        for i in range(0, len(older_messages), chunk_size):
            chunk = older_messages[i:i + chunk_size]
            summary = self._create_checkpoint_summary(chunk, i, i + len(chunk))
            summaries.append(summary)
            checkpoints_created += 1

        # Create summary messages
        summary_messages = self._summaries_to_messages(summaries)

        # Combine: summaries + recent
        optimized = summary_messages + recent_messages
        optimized_tokens = self._estimate_tokens(optimized)

        result = OptimizationResult(
            session_id=session_id,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            tokens_saved=original_tokens - optimized_tokens,
            savings_percentage=(original_tokens - optimized_tokens) / original_tokens * 100
                              if original_tokens > 0 else 0,
            checkpoints_created=checkpoints_created,
            messages_summarized=len(older_messages),
            messages_dropped=0,
            retained_categories={},
            strategy_used="checkpoint",
        )

        return optimized, result

    def _apply_aggressive_strategy(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
    ) -> Tuple[List[Dict[str, Any]], OptimizationResult]:
        """Aggressive strategy: maximum compression."""
        original_tokens = self._estimate_tokens(messages)

        # Keep only most recent messages
        recent_count = min(5, len(messages))  # Reduced to 5
        recent_messages = messages[-recent_count:] if recent_count > 0 else []

        # Create single summary of all older content
        older_messages = messages[:-recent_count] if recent_count < len(messages) else []

        summaries = []
        if older_messages:
            # Extract only critical content
            critical_content = self._extract_critical_content(older_messages)
            summary = MessageSummary(
                start_turn=1,
                end_turn=len(older_messages),
                summary_text=critical_content,
                key_decisions=self._extract_decisions(older_messages),
                key_artifacts=self._extract_artifacts(older_messages),
                token_count_original=self._estimate_tokens(older_messages),
                token_count_summary=self._estimate_tokens_text(critical_content),
            )
            if summary.token_count_original > 0:
                summary.compression_ratio = summary.token_count_summary / summary.token_count_original
            summaries.append(summary)

        # Combine
        summary_messages = self._summaries_to_messages(summaries)
        optimized = summary_messages + recent_messages
        optimized_tokens = self._estimate_tokens(optimized)

        result = OptimizationResult(
            session_id=session_id,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            tokens_saved=original_tokens - optimized_tokens,
            savings_percentage=(original_tokens - optimized_tokens) / original_tokens * 100
                              if original_tokens > 0 else 0,
            checkpoints_created=1 if summaries else 0,
            messages_summarized=len(older_messages),
            messages_dropped=0,
            retained_categories={},
            strategy_used="aggressive",
        )

        return optimized, result

    def _categorize_messages(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[int, str]:
        """Categorize each message by content type."""
        categories = {}

        for i, msg in enumerate(messages):
            content = self._extract_content(msg).lower()
            best_category = "explanations"  # Default
            best_score = 0

            for category, patterns in self.PATTERNS.items():
                score = 0
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    score += len(matches)

                if score > best_score:
                    best_score = score
                    best_category = category

            categories[i] = best_category

        return categories

    def _create_checkpoint_summary(
        self,
        messages: List[Dict[str, Any]],
        start_turn: int,
        end_turn: int,
    ) -> MessageSummary:
        """Create summary of a message chunk."""
        # Extract key content
        all_content = " ".join(self._extract_content(m) for m in messages)

        # Create condensed summary
        decisions = self._extract_decisions(messages)
        artifacts = self._extract_artifacts(messages)

        summary_parts = []
        if decisions:
            summary_parts.append("Decisions: " + "; ".join(decisions[:3]))
        if artifacts:
            summary_parts.append("Artifacts: " + ", ".join(artifacts[:5]))

        summary_text = " | ".join(summary_parts) if summary_parts else \
            f"[Context from turns {start_turn}-{end_turn}]"

        original_tokens = self._estimate_tokens(messages)
        summary_tokens = self._estimate_tokens_text(summary_text)

        return MessageSummary(
            start_turn=start_turn,
            end_turn=end_turn,
            summary_text=summary_text,
            key_decisions=decisions,
            key_artifacts=artifacts,
            token_count_original=original_tokens,
            token_count_summary=summary_tokens,
            compression_ratio=summary_tokens / original_tokens if original_tokens > 0 else 0,
        )

    def _extract_critical_content(self, messages: List[Dict[str, Any]]) -> str:
        """Extract only critical content from messages."""
        critical = []

        for msg in messages:
            content = self._extract_content(msg)

            # Extract code blocks (critical)
            code_blocks = re.findall(r'```[\s\S]*?```', content)
            critical.extend(code_blocks[:2])  # Limit to 2 code blocks

            # Extract file paths
            paths = re.findall(r'/[\w/.-]+\.\w+', content)
            if paths:
                critical.append(f"Files: {', '.join(set(paths[:5]))}")

            # Extract decision statements
            decisions = re.findall(
                r'(?:decided|will|should|must)[^.!?]*[.!?]',
                content,
                re.IGNORECASE
            )
            critical.extend(decisions[:2])

        return "\n".join(critical[:10])  # Limit total critical content

    def _extract_decisions(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key decisions from messages."""
        decisions = []

        for msg in messages:
            content = self._extract_content(msg)
            # Look for decision indicators
            matches = re.findall(
                r'(?:decided|decision|chose|will|should|must)[^.!?]*[.!?]',
                content,
                re.IGNORECASE
            )
            decisions.extend(matches[:2])

        return decisions[:5]  # Limit to 5 decisions

    def _extract_artifacts(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract artifact references (files, functions, etc.)."""
        artifacts = set()

        for msg in messages:
            content = self._extract_content(msg)

            # File paths
            paths = re.findall(r'/[\w/.-]+\.\w+', content)
            artifacts.update(paths)

            # Function/class names (after def/class)
            funcs = re.findall(r'(?:def|class|function)\s+(\w+)', content)
            artifacts.update(funcs)

        return list(artifacts)[:10]

    def _summaries_to_messages(
        self, summaries: List[MessageSummary]
    ) -> List[Dict[str, Any]]:
        """Convert summaries to message format."""
        if not summaries:
            return []

        # Create a single context message
        summary_parts = []
        for s in summaries:
            part = f"[Turns {s.start_turn}-{s.end_turn}]: {s.summary_text}"
            summary_parts.append(part)

        context_text = "\n".join(summary_parts)

        return [{
            "type": "assistant",
            "message": {
                "content": [{
                    "type": "text",
                    "text": f"[CONTEXT SUMMARY]\n{context_text}\n[END SUMMARY]"
                }]
            },
            "is_summary": True,
        }]

    def _extract_content(self, message: Dict[str, Any]) -> str:
        """Extract text content from message."""
        content = message.get("message", {})
        if isinstance(content, dict):
            content = content.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts)
        return str(content)

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate total tokens in messages."""
        total = 0
        for msg in messages:
            content = self._extract_content(msg)
            total += int(len(content.split()) * self.TOKENS_PER_WORD)
        return total

    def _estimate_tokens_text(self, text: str) -> int:
        """Estimate tokens in text."""
        return int(len(text.split()) * self.TOKENS_PER_WORD)

    def _no_optimization_result(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
    ) -> OptimizationResult:
        """Create result for no optimization needed."""
        tokens = self._estimate_tokens(messages)
        return OptimizationResult(
            session_id=session_id,
            original_tokens=tokens,
            optimized_tokens=tokens,
            tokens_saved=0,
            savings_percentage=0.0,
            checkpoints_created=0,
            messages_summarized=0,
            messages_dropped=0,
            retained_categories={},
            strategy_used="none",
        )

    def _save_result(self, result: OptimizationResult) -> None:
        """Save optimization result."""
        with open(self.optimizations_file, 'a') as f:
            data = asdict(result)
            data["timestamp"] = datetime.now().isoformat()
            f.write(json.dumps(data) + "\n")

    def analyze_cost_impact(
        self,
        days: int = 7,
    ) -> CostAnalysis:
        """Analyze cost impact of optimizations over time."""
        results = self._load_results(days)

        if not results:
            return CostAnalysis(
                total_input_tokens=0,
                total_output_tokens=0,
                estimated_cost_original=0.0,
                estimated_cost_optimized=0.0,
                savings=0.0,
                roi_percentage=0.0,
            )

        total_original = sum(r.get("original_tokens", 0) for r in results)
        total_optimized = sum(r.get("optimized_tokens", 0) for r in results)

        # Estimate output tokens (rough: 30% of input)
        output_original = int(total_original * 0.3)
        output_optimized = int(total_optimized * 0.3)

        cost_original = (
            total_original / 1_000_000 * self.COST_PER_M_INPUT +
            output_original / 1_000_000 * self.COST_PER_M_OUTPUT
        )
        cost_optimized = (
            total_optimized / 1_000_000 * self.COST_PER_M_INPUT +
            output_optimized / 1_000_000 * self.COST_PER_M_OUTPUT
        )

        savings = cost_original - cost_optimized
        roi = (savings / cost_original * 100) if cost_original > 0 else 0

        return CostAnalysis(
            total_input_tokens=total_original,
            total_output_tokens=output_original,
            estimated_cost_original=cost_original,
            estimated_cost_optimized=cost_optimized,
            savings=savings,
            roi_percentage=roi,
        )

    def _load_results(self, days: int) -> List[Dict[str, Any]]:
        """Load optimization results from file."""
        results = []

        if not self.optimizations_file.exists():
            return results

        cutoff = datetime.now().timestamp() - (days * 24 * 3600)

        with open(self.optimizations_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        result = json.loads(line)
                        timestamp = result.get("timestamp", "")
                        try:
                            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            if ts.timestamp() >= cutoff:
                                results.append(result)
                        except (ValueError, AttributeError):
                            results.append(result)
                    except json.JSONDecodeError:
                        continue

        return results

    def generate_report(self, days: int = 7) -> str:
        """Generate optimization report."""
        results = self._load_results(days)
        cost_analysis = self.analyze_cost_impact(days)

        if not results:
            return "No optimization data available for the specified period."

        # Calculate statistics
        total_sessions = len(results)
        total_saved = sum(r.get("tokens_saved", 0) for r in results)
        avg_savings_pct = sum(r.get("savings_percentage", 0) for r in results) / total_sessions

        strategies = defaultdict(int)
        for r in results:
            strategies[r.get("strategy_used", "unknown")] += 1

        lines = [
            "",
            "=" * 70,
            "MULTI-TURN OPTIMIZATION REPORT",
            "=" * 70,
            "",
            f"Period: Last {days} days",
            f"Sessions Optimized: {total_sessions}",
            "",
            "─" * 70,
            "TOKEN SAVINGS",
            "─" * 70,
            "",
            f"  Total Tokens Saved: {total_saved:,}",
            f"  Average Savings: {avg_savings_pct:.1f}%",
            f"  Target: >50% on long conversations",
            "",
            "─" * 70,
            "STRATEGY DISTRIBUTION",
            "─" * 70,
            "",
        ]

        for strategy, count in sorted(strategies.items()):
            pct = count / total_sessions * 100
            lines.append(f"  {strategy}: {count} ({pct:.1f}%)")

        lines.extend([
            "",
            "─" * 70,
            "COST IMPACT",
            "─" * 70,
            "",
            f"  Original Cost: ${cost_analysis.estimated_cost_original:.4f}",
            f"  Optimized Cost: ${cost_analysis.estimated_cost_optimized:.4f}",
            f"  Savings: ${cost_analysis.savings:.4f}",
            f"  ROI: {cost_analysis.roi_percentage:.1f}%",
            "",
            "=" * 70,
        ])

        return "\n".join(lines)

    def should_optimize(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if conversation should be optimized."""
        if len(messages) < 20:
            return False

        tokens = self._estimate_tokens(messages)
        return tokens > self.policy.summarization_threshold

    def get_recommendation(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get optimization recommendation for current conversation."""
        tokens = self._estimate_tokens(messages)
        turn_count = len(messages)

        recommendation = {
            "current_tokens": tokens,
            "turn_count": turn_count,
            "should_optimize": False,
            "recommended_strategy": "none",
            "urgency": "low",
            "estimated_savings": 0,
        }

        if tokens < self.policy.summarization_threshold:
            recommendation["message"] = "No optimization needed yet."
            return recommendation

        recommendation["should_optimize"] = True

        if tokens > self.policy.aggressive_threshold:
            recommendation["recommended_strategy"] = "aggressive"
            recommendation["urgency"] = "high"
            recommendation["estimated_savings"] = int(tokens * 0.6)
            recommendation["message"] = (
                f"CRITICAL: {tokens:,} tokens. Aggressive optimization recommended. "
                f"Expected savings: ~{recommendation['estimated_savings']:,} tokens (60%)."
            )
        else:
            recommendation["recommended_strategy"] = "checkpoint"
            recommendation["urgency"] = "medium"
            recommendation["estimated_savings"] = int(tokens * 0.4)
            recommendation["message"] = (
                f"MODERATE: {tokens:,} tokens. Checkpoint summarization recommended. "
                f"Expected savings: ~{recommendation['estimated_savings']:,} tokens (40%)."
            )

        return recommendation


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Turn Conversation Optimizer")
    parser.add_argument(
        "--session",
        type=Path,
        help="Optimize a specific session file"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate optimization report"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days to include in report (default: 7)"
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Force aggressive optimization"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--recommend",
        type=Path,
        help="Get optimization recommendation for session"
    )

    args = parser.parse_args()

    optimizer = MultiTurnOptimizer()

    if args.session:
        # Load and optimize session
        messages = []
        with open(args.session, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        msg = json.loads(line)
                        if msg.get("type") in ("user", "assistant"):
                            messages.append(msg)
                    except json.JSONDecodeError:
                        continue

        optimized, result = optimizer.optimize_conversation(
            messages,
            session_id=args.session.stem,
            force_aggressive=args.aggressive,
        )

        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            print(f"\nSession: {result.session_id}")
            print(f"Strategy: {result.strategy_used}")
            print(f"Original: {result.original_tokens:,} tokens")
            print(f"Optimized: {result.optimized_tokens:,} tokens")
            print(f"Saved: {result.tokens_saved:,} tokens ({result.savings_percentage:.1f}%)")

    elif args.recommend:
        messages = []
        with open(args.recommend, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        msg = json.loads(line)
                        if msg.get("type") in ("user", "assistant"):
                            messages.append(msg)
                    except json.JSONDecodeError:
                        continue

        recommendation = optimizer.get_recommendation(messages)

        if args.json:
            print(json.dumps(recommendation, indent=2))
        else:
            print(f"\n{recommendation['message']}")

    elif args.report:
        print(optimizer.generate_report(days=args.days))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
