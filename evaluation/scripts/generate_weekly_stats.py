#!/usr/bin/env python3
"""
Weekly Stats Generation Script

Generates comprehensive weekly statistics report and saves to file.
Called by systemd timer every Monday at 09:00.

Usage:
    python generate_weekly_stats.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics_tracker import MetricsTracker


def main():
    """Generate weekly stats report."""
    try:
        tracker = MetricsTracker()

        # Generate weekly report
        report = tracker.generate_weekly_report()

        # Save to file
        output_dir = Path.home() / ".claude" / "evaluation" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_file = output_dir / f"weekly_stats_{timestamp}.txt"

        with open(output_file, 'w') as f:
            f.write(report)

        print(f"✅ Weekly report generated: {output_file}")

        # Also generate Tier 2 cost optimization report
        tier2_report = tracker.generate_tier2_report()
        tier2_file = output_dir / f"tier2_report_{timestamp}.txt"

        with open(tier2_file, 'w') as f:
            f.write(tier2_report)

        print(f"✅ Tier 2 report generated: {tier2_file}")

    except Exception as e:
        print(f"❌ Error generating weekly stats: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
