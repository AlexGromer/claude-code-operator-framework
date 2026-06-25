#!/usr/bin/env python3
"""
Test script for cache analytics functionality.
Generates mock cache metrics and validates dashboard output.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from metrics_tracker import MetricsTracker
from cache_analytics import CacheAnalytics


def generate_mock_cache_metrics(count: int = 20, output_file: Path = None):
    """Generate mock cache metrics for testing."""
    if output_file is None:
        output_file = Path.home() / ".claude" / "evaluation" / "data" / "metrics_test.jsonl"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Clear existing test file
    if output_file.exists():
        output_file.unlink()

    print(f"🔧 Generating {count} mock cache metrics...")

    # Create metrics tracker with test file
    test_config = Path.home() / ".claude" / "evaluation" / "config.yaml"
    tracker = MetricsTracker(config_path=test_config)

    # Temporarily override data path
    original_path = tracker.data_path
    tracker.data_path = output_file

    # Generate metrics over the last week
    now = datetime.now(timezone.utc)

    for i in range(count):
        # Vary metrics to simulate real usage
        cached_tokens = 12000 + (i * 100)  # 12k-14k cached
        fresh_tokens = 3000 - (i * 50)      # 3k-2k fresh
        latency_ms = 800 + (i * 10)         # 800-1000ms

        # Simulate different hit rates
        if i % 5 == 0:
            # Occasionally poor cache hit
            cached_tokens = 5000
            fresh_tokens = 10000

        tracker.collect_cache_metric(
            cached_tokens=cached_tokens,
            fresh_tokens=fresh_tokens,
            latency_ms=latency_ms,
            model="claude-sonnet-4-5-20250929"
        )

    # Restore original path
    tracker.data_path = original_path

    print(f"✅ Mock metrics generated: {output_file}")
    return output_file


def test_cache_analytics():
    """Test cache analytics functionality."""
    print("\n" + "="*80)
    print("TESTING CACHE ANALYTICS")
    print("="*80 + "\n")

    # Generate test data
    test_file = generate_mock_cache_metrics(count=20)

    # Test analytics
    print("\n📊 Testing CacheAnalytics...")
    analytics = CacheAnalytics(metrics_file=test_file)

    # Test loading metrics
    metrics = analytics.load_cache_metrics(period="all")
    print(f"   Loaded {len(metrics)} cache metrics")
    assert len(metrics) == 20, f"Expected 20 metrics, got {len(metrics)}"

    # Test statistics calculation
    stats = analytics.calculate_statistics(metrics)
    print(f"   Average hit rate: {stats['avg_hit_rate']*100:.1f}%")
    print(f"   Total savings: ${stats['total_savings']:.2f}")
    print(f"   Total requests: {stats['total_requests']}")

    assert 'error' not in stats, "Statistics calculation failed"
    assert stats['total_requests'] == 20, "Incorrect request count"
    assert stats['avg_hit_rate'] > 0, "Hit rate should be > 0"
    assert stats['total_savings'] > 0, "Savings should be > 0"

    # Test report generation
    print("\n📄 Testing report generation...")
    report = analytics.generate_report(period="all", format="markdown")
    assert "Cache Analytics Dashboard" in report, "Report missing title"
    assert "Total Requests" in report, "Report missing summary"
    assert "Recommendations" in report, "Report missing recommendations"

    print(f"   Report length: {len(report)} characters")

    # Test JSON format
    json_report = analytics.generate_report(period="all", format="json")
    json_data = json.loads(json_report)
    assert 'total_requests' in json_data, "JSON report missing data"

    print("\n📋 Sample Report (first 500 chars):")
    print("-" * 80)
    print(report[:500] + "...")
    print("-" * 80)

    # Cleanup test file
    test_file.unlink()
    print(f"\n🧹 Cleaned up test file: {test_file}")

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80 + "\n")


def test_metrics_tracker_integration():
    """Test integration with metrics_tracker.py."""
    print("\n" + "="*80)
    print("TESTING METRICS_TRACKER INTEGRATION")
    print("="*80 + "\n")

    # Create temporary test file
    test_file = Path(tempfile.gettempdir()) / "claude_metrics_integration_test.jsonl"
    test_file.unlink(missing_ok=True)

    # Create metrics tracker
    config_path = Path.home() / ".claude" / "evaluation" / "config.yaml"
    tracker = MetricsTracker(config_path=config_path)

    # Override data path
    original_path = tracker.data_path
    tracker.data_path = test_file

    print("📝 Testing collect_cache_metric() method...")

    # Test collecting cache metrics
    tracker.collect_cache_metric(
        cached_tokens=15000,
        fresh_tokens=3000,
        latency_ms=850,
        model="claude-sonnet-4-5-20250929"
    )

    print("   ✓ Cache metric collected")

    # Verify metric was written
    assert test_file.exists(), "Metrics file not created"

    with open(test_file, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"

        metric = json.loads(lines[0])
        assert metric['metric_type'] == 'cache', "Incorrect metric type"
        assert 'metadata' in metric, "Missing metadata"
        assert 'hit_rate' in metric['metadata'], "Missing hit_rate in metadata"
        assert 'savings' in metric['metadata'], "Missing savings in metadata"

        print(f"   ✓ Metric format validated")
        print(f"   Hit rate: {metric['metadata']['hit_rate']*100:.1f}%")
        print(f"   Savings: ${metric['metadata']['savings']:.4f}")

    # Restore original path
    tracker.data_path = original_path

    # Cleanup
    test_file.unlink()

    print("\n✅ INTEGRATION TEST PASSED!")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        # Run tests
        test_metrics_tracker_integration()
        test_cache_analytics()

        print("\n🎉 ALL TESTS SUCCESSFUL!")
        print("\nNext steps:")
        print("  1. Activate wrapper: bash ~/.claude/evaluation/activate_wrapper.sh")
        print("  2. Reload shell: source ~/.bashrc  (or ~/.zshrc)")
        print("  3. Use Claude as normal - dashboard will display on exit")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
