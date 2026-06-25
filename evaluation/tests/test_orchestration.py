#!/usr/bin/env pytest
"""Tests for orchestration tools integration."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "tools"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
