#!/usr/bin/env python3
"""
Sliding Window Context Strategy
TIER 2B Task 16: GAP-COST-IMPL-004

Implements sliding window algorithm for multi-turn conversations (>20 turns).
Reduces token usage by retaining recent messages + critical context only.

Target: -50% token usage on long conversations (>20 turns)
ROI: 40-60% cost reduction with -5% quality impact
"""

import json
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Message:
    """Represents a conversation message."""
    role: str  # user, assistant, system
    content: str
    index: int  # Position in original history
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WindowConfig:
    """Configuration for sliding window strategy."""
    window_size: int = 20  # Number of recent turns to always keep
    min_history: int = 5   # Minimum history to retain (safety threshold)
    max_history: int = 200  # Maximum history before forced truncation
    always_retain_code: bool = True  # Always keep code blocks
    always_retain_decisions: bool = True  # Always keep critical decisions
    always_retain_system: bool = True  # Always keep system messages


@dataclass
class WindowStats:
    """Statistics about sliding window operation."""
    original_count: int
    windowed_count: int
    retained_critical: int
    retained_recent: int
    dropped_count: int
    compression_ratio: float
    estimated_token_savings: int


class SlidingWindow:
    """
    Implements sliding window strategy for context management.

    TIER 2B Task 16 (GAP-COST-IMPL-004): Sliding Window Context Strategy
    - Retains recent messages (window_size)
    - Retains critical context (code, decisions, errors)
    - Drops non-critical explanations and casual discussion
    """

    # Patterns for detecting critical content
    CODE_BLOCK_PATTERN = r'```[\s\S]*?```'
    FILE_PATH_PATTERN = r'/[\w\-/.]+\.\w+'
    ERROR_PATTERN = r'\b(error|exception|failed|crash|bug)\b'
    DECISION_KEYWORDS = [
        'decided', 'choosing', 'selected', 'implemented',
        'architecture', 'design decision', 'trade-off',
        'critical', 'important', 'must', 'require',
    ]

    def __init__(self, config: Optional[WindowConfig] = None):
        """
        Initialize sliding window with configuration.

        Args:
            config: WindowConfig object (defaults to WindowConfig())
        """
        self.config = config or WindowConfig()

    def is_critical_message(self, message: Message) -> Tuple[bool, str]:
        """
        Determine if message contains critical information that must be retained.

        Args:
            message: Message object to analyze

        Returns:
            Tuple of (is_critical: bool, reason: str)
        """
        content = message.content
        reasons = []

        # Always retain system messages
        if message.role == 'system' and self.config.always_retain_system:
            return True, "system message"

        # Check for code blocks
        if self.config.always_retain_code:
            if re.search(self.CODE_BLOCK_PATTERN, content, re.MULTILINE):
                reasons.append("contains code")

        # Check for file paths (likely code references)
        if self.config.always_retain_code:
            if re.search(self.FILE_PATH_PATTERN, content):
                reasons.append("contains file paths")

        # Check for errors/exceptions
        if re.search(self.ERROR_PATTERN, content, re.IGNORECASE):
            reasons.append("contains error/exception")

        # Check for decision keywords
        if self.config.always_retain_decisions:
            content_lower = content.lower()
            for keyword in self.DECISION_KEYWORDS:
                if keyword in content_lower:
                    reasons.append(f"decision keyword: '{keyword}'")
                    break

        # Check for user questions (important to retain context)
        if message.role == 'user':
            if content.endswith('?') or content.startswith(('what', 'how', 'why', 'when', 'where')):
                reasons.append("user question")

        # Check for tool usage (function calls, tool results)
        if message.metadata and 'tool_use' in message.metadata:
            reasons.append("tool usage")

        is_critical = len(reasons) > 0
        reason_str = ", ".join(reasons) if reasons else "not critical"

        return is_critical, reason_str

    def apply_sliding_window(
        self,
        history: List[Message],
        custom_retention_fn: Optional[Callable[[Message], bool]] = None
    ) -> Tuple[List[Message], WindowStats]:
        """
        Apply sliding window strategy to conversation history.

        Args:
            history: List of Message objects (chronological order)
            custom_retention_fn: Optional custom function to determine retention
                                 (overrides default is_critical_message)

        Returns:
            Tuple of (windowed_history, stats)
        """
        if len(history) <= self.config.min_history:
            # Too short to apply window, return as-is
            stats = WindowStats(
                original_count=len(history),
                windowed_count=len(history),
                retained_critical=0,
                retained_recent=len(history),
                dropped_count=0,
                compression_ratio=1.0,
                estimated_token_savings=0
            )
            return history, stats

        # Split into recent window and older messages
        window_start_idx = max(0, len(history) - self.config.window_size)
        older_messages = history[:window_start_idx]
        recent_messages = history[window_start_idx:]

        # Determine which older messages to retain
        retention_fn = custom_retention_fn or (lambda m: self.is_critical_message(m)[0])

        retained_older = []
        for msg in older_messages:
            if retention_fn(msg):
                retained_older.append(msg)

        # Combine: critical older messages + recent window
        windowed_history = retained_older + recent_messages

        # Enforce max_history limit (safety)
        if len(windowed_history) > self.config.max_history:
            # Drop oldest non-critical messages
            excess = len(windowed_history) - self.config.max_history
            # Keep all recent, drop from older critical
            windowed_history = windowed_history[excess:]

        # Calculate stats
        dropped_count = len(history) - len(windowed_history)
        compression_ratio = len(windowed_history) / len(history) if len(history) > 0 else 1.0

        # Estimate token savings (rough: 200 tokens/message average)
        AVG_TOKENS_PER_MESSAGE = 200
        estimated_token_savings = dropped_count * AVG_TOKENS_PER_MESSAGE

        stats = WindowStats(
            original_count=len(history),
            windowed_count=len(windowed_history),
            retained_critical=len(retained_older),
            retained_recent=len(recent_messages),
            dropped_count=dropped_count,
            compression_ratio=compression_ratio,
            estimated_token_savings=estimated_token_savings
        )

        return windowed_history, stats

    def format_stats(self, stats: WindowStats) -> str:
        """
        Format window statistics for display.

        Args:
            stats: WindowStats object

        Returns:
            Formatted string
        """
        lines = [
            f"📊 Sliding Window Statistics:",
            f"  Original Messages: {stats.original_count}",
            f"  Windowed Messages: {stats.windowed_count}",
            f"  Retained Critical: {stats.retained_critical} (older messages)",
            f"  Retained Recent: {stats.retained_recent} (window)",
            f"  Dropped: {stats.dropped_count}",
            f"  Compression: {stats.compression_ratio:.1%}",
            f"  Estimated Token Savings: ~{stats.estimated_token_savings:,} tokens",
        ]

        return "\n".join(lines)

    @staticmethod
    def parse_session_messages(session_file: Path) -> List[Message]:
        """
        Parse session JSONL file into Message objects.

        Args:
            session_file: Path to session JSONL file

        Returns:
            List of Message objects
        """
        messages = []

        with open(session_file, 'r') as f:
            for idx, line in enumerate(f):
                try:
                    entry = json.loads(line)

                    # Skip non-message entries (file-history-snapshot, etc.)
                    if 'message' not in entry:
                        continue

                    message_obj = entry['message']

                    # Extract role and content
                    role = message_obj.get('role', 'unknown')
                    content = message_obj.get('content', '')

                    # Handle content that's a list (tool use, etc.)
                    if isinstance(content, list):
                        # Concatenate text blocks
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                        content = '\n'.join(text_parts)

                    # Skip empty content
                    if not content or (isinstance(content, str) and not content.strip()):
                        continue

                    messages.append(Message(
                        role=role,
                        content=content if isinstance(content, str) else str(content),
                        index=len(messages),  # Use actual message index, not line index
                        timestamp=entry.get('timestamp'),
                        metadata=entry.get('metadata')
                    ))

                except (json.JSONDecodeError, KeyError):
                    continue

        return messages

    def analyze_session(self, session_file: Path) -> Dict[str, Any]:
        """
        Analyze session and provide windowing recommendations.

        Args:
            session_file: Path to session JSONL file

        Returns:
            Dictionary with analysis results
        """
        messages = self.parse_session_messages(session_file)

        if len(messages) <= self.config.min_history:
            return {
                "should_apply_window": False,
                "reason": f"Session too short ({len(messages)} messages, min: {self.config.min_history})",
                "message_count": len(messages),
            }

        # Apply sliding window
        windowed_messages, stats = self.apply_sliding_window(messages)

        # Count critical messages by type
        critical_breakdown = {
            "code": 0,
            "decisions": 0,
            "errors": 0,
            "user_questions": 0,
            "system": 0,
        }

        for msg in messages[:len(messages) - self.config.window_size]:
            is_crit, reason = self.is_critical_message(msg)
            if is_crit:
                if "code" in reason:
                    critical_breakdown["code"] += 1
                if "decision" in reason:
                    critical_breakdown["decisions"] += 1
                if "error" in reason:
                    critical_breakdown["errors"] += 1
                if "question" in reason:
                    critical_breakdown["user_questions"] += 1
                if "system" in reason:
                    critical_breakdown["system"] += 1

        return {
            "should_apply_window": True,
            "message_count": len(messages),
            "stats": stats,
            "critical_breakdown": critical_breakdown,
            "recommendation": (
                f"Apply sliding window: Keep {stats.windowed_count}/{stats.original_count} messages "
                f"({stats.compression_ratio:.0%}), save ~{stats.estimated_token_savings:,} tokens"
            )
        }


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Sliding Window Context Strategy")
    parser.add_argument('--session-file', type=Path, help="Session JSONL file to analyze")
    parser.add_argument('--window-size', type=int, default=20,
                       help="Window size (default: 20)")
    parser.add_argument('--analyze', action='store_true',
                       help="Analyze session and show recommendations")
    parser.add_argument('--test', action='store_true',
                       help="Run test suite")

    args = parser.parse_args()

    config = WindowConfig(window_size=args.window_size)
    window = SlidingWindow(config)

    if args.test:
        # Test suite
        print("=" * 70)
        print("SLIDING WINDOW TEST SUITE")
        print("=" * 70)
        print()

        # Test 1: Short history (no windowing)
        print("Test 1: Short history (no windowing)")
        short_history = [
            Message(role="user", content="Hello", index=0),
            Message(role="assistant", content="Hi there!", index=1),
        ]
        windowed, stats = window.apply_sliding_window(short_history)
        print(window.format_stats(stats))
        assert len(windowed) == len(short_history), "Short history should not be windowed"
        print("✅ PASS\n")

        # Test 2: Long history with code (retain critical)
        print("Test 2: Long history with code (retain critical)")
        long_history = []
        for i in range(30):
            if i == 5:
                # Critical message with code
                long_history.append(Message(
                    role="assistant",
                    content="Here's the implementation:\n```python\ndef hello():\n    print('hello')\n```",
                    index=i
                ))
            else:
                long_history.append(Message(
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Message {i}: casual discussion",
                    index=i
                ))

        windowed, stats = window.apply_sliding_window(long_history)
        print(window.format_stats(stats))

        # Verify code message was retained
        code_msg_retained = any("```python" in msg.content for msg in windowed)
        assert code_msg_retained, "Code message should be retained"
        assert stats.retained_critical >= 1, "Should have retained critical message"
        print("✅ PASS\n")

        # Test 3: Compression ratio
        print("Test 3: Compression ratio")
        print(f"  Compression: {stats.compression_ratio:.1%}")
        assert stats.compression_ratio < 1.0, "Should have compression < 100%"
        print("✅ PASS\n")

        print("=" * 70)
        print("All tests passed!")

    elif args.session_file:
        if not args.session_file.exists():
            print(f"❌ Error: Session file not found: {args.session_file}")
            return

        if args.analyze:
            # Analyze session
            analysis = window.analyze_session(args.session_file)

            print("=" * 70)
            print("SLIDING WINDOW ANALYSIS")
            print("=" * 70)
            print()

            print(f"Session File: {args.session_file}")
            print(f"Messages: {analysis['message_count']}")
            print()

            if not analysis['should_apply_window']:
                print(f"⚠️ {analysis['reason']}")
            else:
                print(window.format_stats(analysis['stats']))
                print()
                print("Critical Content Breakdown:")
                for content_type, count in analysis['critical_breakdown'].items():
                    if count > 0:
                        print(f"  • {content_type}: {count}")
                print()
                print(f"💡 Recommendation: {analysis['recommendation']}")

            print("=" * 70)

        else:
            # Apply windowing
            messages = window.parse_session_messages(args.session_file)
            windowed, stats = window.apply_sliding_window(messages)

            print(window.format_stats(stats))
            print()
            print(f"Output: {len(windowed)} messages (original: {len(messages)})")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
