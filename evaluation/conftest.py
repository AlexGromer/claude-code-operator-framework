"""Pytest configuration for evaluation tests.

Ensures evaluation/ is in sys.path so that imports like
'from costs.agent_cost_tracker import ...' work regardless
of the directory from which pytest is invoked.
"""

import sys
from pathlib import Path

# Add evaluation/ directory to sys.path
eval_dir = str(Path(__file__).parent)
if eval_dir not in sys.path:
    sys.path.insert(0, eval_dir)
