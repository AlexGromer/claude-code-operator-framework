# Module: Testing Reference (Our Setup)
# On-demand reference: Load when writing tests or debugging test failures
# Version: 2.0.0 | Compacted: 2026-02-25

---

## Test Suite Stats

**1,640+ tests across 77 files** — all passing required before commits.

| Location | Files | Coverage |
|----------|-------|----------|
| `~/.claude/evaluation/tests/` | ~75 files | Tools, hooks, budget, safety |
| `~/.claude/evaluation/` | 3 root-level | agent_cost_tracker, cache_analytics, hallucination |

**Run tests:**
```bash
cd ~/.claude/evaluation && python -m pytest tests/ -v
cd ~/.claude/evaluation && python -m pytest tests/test_hooks_integration.py -v
cd ~/.claude/evaluation && python -m pytest tests/test_budget_manager.py -v
```

---

## Framework & Structure

**Framework:** pytest with `conftest.py` at `~/.claude/evaluation/conftest.py`

```python
# conftest.py adds evaluation/ to sys.path — allows:
from costs.budget_manager import BudgetManager
from agent_metrics import AgentMetrics
```

**Imports pattern in test files:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude" / "tools"))
# or: sys.path.insert(0, '/home/user/.claude/evaluation')

from agent_test_harness import run_test_case, TestCase, TestType
```

**Fixtures pattern (tmp_path for file-based tools):**
```python
@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "eval_data"
    d.mkdir()
    return d

@pytest.fixture
def manager(data_dir):
    return BudgetManager(data_dir=data_dir)
```

---

## Test File Map (Key Tests)

| File | Tests What |
|------|-----------|
| `test_hooks_integration.py` | All 54 hooks: syntax, imports, structure, behavior |
| `test_budget_manager.py` | BudgetManager, BudgetConfig, SpendingRecord |
| `test_agent_harness.py` | agent_test_harness.py tool |
| `test_mcp_tool_tester.py` | MCP tool schema + server mock tests |
| `test_safety_scenarios.py` | SAFETY_SCENARIOS, run_category, run_all |
| `test_evaluation_core.py` | agent_metrics.py, task_completion.py, latency_tracker.py |
| `test_hallucination_detector.py` | Hallucination detection logic |
| `test_code_review_checks.py` | code_review_checks.py tool |
| `test_budget_manager.py` | Budget enforcement, can_spend(), alerts |

---

## Hook Integration Testing Pattern

`test_hooks_integration.py` is the canonical hook test. Structure:

```python
HOOKS_DIR = Path('/home/user/.claude/hooks')
EVAL_HOOKS_DIR = Path('/home/user/.claude/evaluation/hooks')

class TestHookSyntax:
    @pytest.mark.parametrize("hook_path", get_all_hooks(), ids=lambda p: p.name)
    def test_hook_compiles(self, hook_path):
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', str(hook_path)],
            capture_output=True, text=True
        )
        assert result.returncode == 0

class TestHookStructure:
    def test_has_shebang(self, hook_path): ...
    def test_has_main_block(self, hook_path): ...
    def test_has_docstring(self, hook_path): ...

class TestSecurityHooks:
    def test_input_validation_blocks_malicious(self): ...
    def test_input_validation_passes_safe(self): ...

class TestEvaluationHooks:
    def test_cost_tracking_records(self): ...
    def test_simple_metrics_accepts_valid(self): ...
```

Hooks require: shebang `#!/usr/bin/env python3`, docstring, main block or direct execution, stdin JSON input handling.

---

## MCP Tool Testing Pattern

```python
# mcp_tool_tester.py wraps our MCP tools for testability
from mcp_tool_tester import run_tool_test, run_server_tests, validate_tool_schema, MCP_TEST_CASES

# Validate naming convention (mcp__server__tool)
result = validate_tool_schema("mcp__github__search_repositories")
assert result["valid"] is True

result = validate_tool_schema("bad_tool_name")
assert result["valid"] is False

# Run server test suite with mock=True (no real API calls)
results = run_server_tests("github", mock=True)
assert results.get("total", 0) > 0
```

**MCP tool naming rule:** `mcp__<server>__<tool>` — double underscore separators. Tests validate this schema before anything else.

---

## Agent Behavior Testing Pattern

```python
from agent_test_harness import run_test_case, TestCase, TestType, BEHAVIORAL_SCENARIOS

# Standard test case
test_case = TestCase(
    test_id="test-1",
    name="Test Pass",
    test_type=TestType.UNIT,
    description="Should pass",
    input_data={"value": 1},
    expected_output={"behavior": "simulated", "success": True},
)
result = run_test_case(test_case)
assert result.status == "passed"

# compare_outputs does subset matching for dicts
assert compare_outputs({"a": 1, "b": 2}, {"a": 1})   # True (subset)
assert not compare_outputs({"a": 1}, {"a": 1, "b": 2})  # False (missing key)
```

**BEHAVIORAL_SCENARIOS** — predefined scenarios in agent_test_harness.py for common agent workflows.

---

## Safety Testing Pattern

```python
from safety_test_scenarios import SAFETY_SCENARIOS, run_category, run_all

# SAFETY_SCENARIOS dict: category → list of test cases
assert len(SAFETY_SCENARIOS) > 0

# Run by category
results = run_category("permission_boundaries")
assert isinstance(results, list)

# Run everything — returns report dict
report = run_all()
assert report is not None
```

**Safety scenario categories** (from `~/.claude/tools/safety_test_scenarios.py`):
- `permission_boundaries` — file system, network, credential access
- `resource_limits` — token/tool call limits, timeout
- `unauthorized_actions` — destructive commands, data exfiltration patterns
- Unauthorized patterns scanned in Bash tool calls: `rm -rf`, `/etc/passwd`, `chmod 777`, `nc -e`, `base64.*curl`

---

## Budget System Testing

```python
from costs.budget_manager import BudgetConfig, BudgetLevel, BudgetManager, BudgetStatus

@pytest.fixture
def manager(tmp_path):
    return BudgetManager(data_dir=tmp_path / "eval_data")

def test_can_spend_blocks_over_budget(manager):
    # Record spending up to limit
    manager.record_spending(SpendingRecord(cost_usd=9.99, ...))
    assert manager.can_spend(0.02) is False  # Would exceed limit

def test_alert_threshold(manager):
    # 80% of budget triggers warning alert
    manager.record_spending(SpendingRecord(cost_usd=8.00, ...))
    status = manager.get_status()
    assert status.alert_level == BudgetAlert.WARNING
```

**Critical:** BudgetManager uses file locking for `budget_spending.jsonl`. Tests must use `tmp_path` to avoid race conditions with live hooks.

---

## Evaluation Metrics We Track

From `~/.claude/evaluation/` (`agent_metrics.py`, `latency_tracker.py`, `metrics_tracker.py`):

| Metric | Target | Tracked In |
|--------|--------|-----------|
| Accuracy | >0.85 | mcp__metrics__rate_response |
| Hallucination rate | <0.05 | hallucination_check_hook.py |
| Tool error rate | <0.02 | tool_error_hook.py |
| Session cost | <$10/day | budget_manager.py |
| TTFT / latency | logged | latency_tracker.py |

**MCP metrics tool** (use after completing tasks):
```python
mcp__metrics__rate_response(accuracy_score=0.95, has_hallucination=False, task_description="...")
mcp__metrics__collect_metric(metric_type="latency", value=2.3, task_description="...")
```

---

## Test Requirements (Our Rules)

From `mandatory-checks.md` + `code-before-write.md`:

1. Run tests after new features, bug fixes, refactoring, before commits/PRs
2. **Never** skip tests silently or commit with failing tests
3. Default assumption: **test is RIGHT, code is WRONG** — fix implementation, not test
4. Test expected behavior, not written code (TDD)
5. Secrets scan before commit: `gitleaks detect --source . --verbose`

**Coverage target: 95%** for our tools. Failing hook = block commit until fixed.

---

## Adding New Tests

When creating a new tool in `~/.claude/tools/` or `~/.claude/evaluation/`:

```python
# File: ~/.claude/evaluation/tests/test_my_new_tool.py
#!/usr/bin/env pytest
"""Tests for my_new_tool.py."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "tools"))
from my_new_tool import MainClass, main_function

class TestMyNewTool:
    def test_basic_functionality(self):
        result = main_function({"input": "value"})
        assert result is not None

    def test_error_handling(self):
        with pytest.raises(ValueError):
            main_function({})  # Missing required field

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

Key: always add `sys.path.insert` for the source directory, use `tmp_path` for file operations, test error paths.
