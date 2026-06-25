# Hook Integration Tests

## Overview

`test_hooks_integration.py` provides comprehensive integration testing for all Claude Code hooks.

## Coverage

**Total Hooks Tested:** 54 hooks
- `/home/user/.claude/hooks/` — Main hooks (33)
- `/home/user/.claude/evaluation/hooks/` — Evaluation hooks (21)

## Test Categories

### 1. **TestHookSyntax** (54 tests)
- Verifies all hooks compile without syntax errors
- Uses `python -m py_compile`

### 2. **TestHookImports** (54 tests)
- Verifies hooks can be loaded as modules
- Tests import spec creation

### 3. **TestHookStructure** (162 tests)
- Verifies shebang presence (`#!/usr/bin/env python3`)
- Verifies execution logic (main block or direct execution)
- Verifies module docstrings

### 4. **TestSecurityHooks** (2 tests)
- Tests `input_validation_hook` with malicious input
- Tests `input_validation_hook` with safe input

### 5. **TestEvaluationHooks** (2 tests)
- Tests `cost_tracking_hook` records costs
- Tests `simple_metrics_hook` accepts valid input

### 6. **TestSessionHooks** (1 test)
- Tests `session_health_check` runs without error

### 7. **TestToolHooks** (4 tests)
- Tests tool execution hooks accept standard input

### 8. **TestContentHooks** (1 test)
- Tests `code_review_hook` runs on Write tool

### 9. **TestInfrastructureHooks** (1 test)
- Tests `budget_check_hook` structure

### 10. **TestHITLHooks** (1 test)
- Tests `usage_limit_hook` structure

### 11. **TestHookExecution** (2 tests)
- Tests hooks handle empty stdin gracefully
- Tests hooks handle invalid JSON gracefully

### 12. **TestHookCategories** (2 tests)
- Verifies all hooks are categorized
- Reports hook counts by category

### 13. **TestHookPerformance** (54 tests)
- Verifies hooks complete within 5 seconds

## Running Tests

### All tests:
```bash
cd /home/user/.claude/evaluation
python -m pytest tests/test_hooks_integration.py -v
```

### Specific test class:
```bash
python -m pytest tests/test_hooks_integration.py::TestSecurityHooks -v
```

### Specific test:
```bash
python -m pytest tests/test_hooks_integration.py::TestSecurityHooks::test_input_validation_hook_blocks_injection -v
```

### With output:
```bash
python -m pytest tests/test_hooks_integration.py -v -s
```

## Test Results

**Status:** ✅ **339 passed, 1 skipped**
- Total test cases: 340
- Execution time: ~30-40 seconds
- Coverage: 100% of hooks (54/54)

## Hook Categories

| Category | Count | Examples |
|----------|-------|----------|
| security | 8 | input_validation, atlas_pre_request, redteam |
| session | 8 | session_health_check, session_end, state_persistence |
| evaluation | 13 | cost_tracking, agent_metrics, hallucination_check |
| tool | 6 | tool_execution, tool_success, tool_failure |
| content | 6 | code_review, rag_validation, semantic_routing |
| infrastructure | 6 | budget_check, config_integrity, benchmark |
| hitl | 3 | hitl_approval, usage_limit, hitl_workflow |
| other | 4 | computer_use, memgpt_context, vector_db |

## Key Features

1. **Comprehensive Coverage**: Every hook tested for syntax, imports, and structure
2. **Functional Tests**: Critical hooks tested with real inputs (security, evaluation)
3. **Performance Tests**: All hooks must complete within 5 seconds
4. **Error Handling**: Tests verify hooks handle edge cases (empty stdin, invalid JSON)
5. **Categorization**: All hooks organized by function

## Integration with CI/CD

These tests can be integrated into CI/CD pipelines:

```bash
# In .github/workflows/test.yml or similar
- name: Test Hooks
  run: |
    cd /home/user/.claude/evaluation
    python -m pytest tests/test_hooks_integration.py -v --junitxml=test-results.xml
```

## Maintenance

When adding new hooks:
1. Add hook to appropriate category in `HOOK_CATEGORIES`
2. If hook has special behavior, add specific test in corresponding TestClass
3. Run full test suite to ensure new hook passes all baseline tests

## Dependencies

- pytest
- Python 3.8+
- All hooks must be in standard locations

## Notes

- One test skipped: `debug_env_hook.py` docstring test (simple utility hook)
- Some hooks are tested at structure level only (import + syntax)
- Critical hooks (security, evaluation) have functional tests with mock inputs
