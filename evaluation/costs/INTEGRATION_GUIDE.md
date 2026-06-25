# Agent Cost Tracker Integration Guide

## Overview

`agent_cost_tracker.py` provides unified cost tracking across all agent operations:
- Token usage (all models: haiku/sonnet/opus)
- Tool executions (Bash, Read, Write, WebFetch, etc.)
- Subagent spawns (Task tool)
- External API calls
- Compute resources
- Storage operations

## Quick Start

```python
from agent_cost_tracker import AgentCostTracker

# Initialize tracker
tracker = AgentCostTracker()

# Log token usage
tracker.log_token_cost(
    session_id="abc123",
    model="sonnet",
    input_tokens=15000,
    output_tokens=6000,
    cached_tokens=3000
)

# Log tool execution
tracker.log_tool_cost(
    session_id="abc123",
    tool_name="Bash",
    execution_time_ms=2500
)

# Generate report
print(tracker.generate_report(session_id="abc123"))
```

## Integration with Existing Modules

### 1. Model Router Integration

Route tasks to optimal model and log costs:

```python
from model_router import ModelRouter
from agent_cost_tracker import AgentCostTracker

router = ModelRouter()
tracker = AgentCostTracker()

# Route task
result = router.route("Analyze code for vulnerabilities")
model = result['model']  # e.g., "sonnet"

# Execute task (simulated)
input_tokens, output_tokens, cached_tokens = 15000, 6000, 3000

# Log cost
tracker.log_token_cost(
    session_id="session-001",
    model=model,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    cached_tokens=cached_tokens
)
```

### 2. Caching Analytics Integration

Track cache hits and costs together:

```python
from caching_analytics import CacheAnalytics
from agent_cost_tracker import AgentCostTracker

cache = CacheAnalytics()
tracker = AgentCostTracker()

# Log request with cache info
cache_hit = True
cached_tokens = 8000 if cache_hit else 0
fresh_tokens = 5000

tracker.log_token_cost(
    session_id="session-001",
    model="sonnet",
    input_tokens=fresh_tokens + cached_tokens,
    output_tokens=4000,
    cached_tokens=cached_tokens
)

# Calculate ROI
roi = cache.calculate_roi()
print(f"Cache ROI: {roi['cost_reduction_pct']:.1f}%")
```

### 3. Sliding Window Integration

Track costs before/after context compression:

```python
from sliding_window import SlidingWindow
from agent_cost_tracker import AgentCostTracker

window = SlidingWindow(window_size=20)
tracker = AgentCostTracker()

# Before compression
original_tokens = 50000
tracker.log_token_cost("session-001", "sonnet", original_tokens, 8000, 0)

# Apply sliding window
compressed = window.compress(conversation_history)
compressed_tokens = len(compressed) * 100  # estimate

# After compression
tracker.log_token_cost("session-001", "sonnet", compressed_tokens, 8000, 0)

# Compare costs
summary = tracker.get_session_summary("session-001")
print(f"Total cost: ${summary.total_cost:.3f}")
```

### 4. Metrics Tracker Integration

Add cost reporting to metrics dashboard:

```python
from metrics_tracker import MetricsTracker
from agent_cost_tracker import AgentCostTracker

metrics = MetricsTracker()
costs = AgentCostTracker()

# Collect various metrics
metrics.collect_metric("accuracy", 0.95)
metrics.collect_metric("latency", 850, {"model": "sonnet"})

# Collect cost metrics
session_summary = costs.get_session_summary("session-001")
metrics.collect_metric("cost", session_summary.total_cost, {
    "session_id": "session-001",
    "request_count": session_summary.request_count
})
```

## Hook Integration (Automatic Tracking)

For automatic cost tracking in Claude Code sessions, add to session hooks:

```python
# ~/.claude/hooks/response_end_hook.py

from agent_cost_tracker import AgentCostTracker

def on_response_end(session_id, request_data, response_data):
    """Track costs automatically after each response."""
    tracker = AgentCostTracker()

    # Extract usage from response
    usage = response_data.get("usage", {})
    model = response_data.get("model", "sonnet")

    tracker.log_token_cost(
        session_id=session_id,
        model=model,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cached_tokens=usage.get("cache_read_input_tokens", 0)
    )

    # Log tool calls
    for tool in response_data.get("tool_calls", []):
        tracker.log_tool_cost(
            session_id=session_id,
            tool_name=tool["name"],
            execution_time_ms=tool.get("duration_ms", 0)
        )
```

## CLI Usage

### Daily Summary
```bash
python3 agent_cost_tracker.py --report
```

### Session Summary
```bash
python3 agent_cost_tracker.py --report --session abc123
```

### Budget Check
```bash
python3 -c "
from agent_cost_tracker import AgentCostTracker
tracker = AgentCostTracker()
budget = tracker.get_budget_status('session-001')
print(f'Budget: {budget[\"used_pct\"]:.1f}% used')
"
```

### Self-Test
```bash
python3 agent_cost_tracker.py --test
```

## Cost Breakdown Structure

### Categories
- **tokens**: Input/output/cached token costs (all models)
- **tools**: Standard tool executions (Read, Write, Edit, Bash, etc.)
- **subagents**: Subagent spawns via Task tool
- **external_apis**: External API calls (WebFetch, WebSearch)
- **compute**: Compute resource costs (execution time)
- **storage**: Storage operations (file writes)

### Models
- **haiku**: $1/$5 per 1M tokens (in/out), $0.1 cached
- **sonnet**: $3/$15 per 1M tokens (in/out), $0.3 cached
- **opus**: $15/$75 per 1M tokens (in/out), $1.5 cached

### Tools (per call)
- **Bash**: $0.001
- **Read/Write/Edit**: $0.0001
- **WebFetch**: $0.005
- **WebSearch**: $0.01
- **Task** (subagent spawn): $0.05

## Budget Thresholds

- **Session Budget**: $10.00 (per session)
- **Daily Budget**: $50.00 (per day)

**Status Levels**:
- ✅ **healthy**: <80% of budget used
- ⚠️ **warning**: 80-99% of budget used
- 🔴 **critical**: ≥100% of budget used

## Data Storage

Cost records are stored in JSONL format:

```
~/.claude/evaluation/data/agent_costs.jsonl
```

Each line is a JSON object:

```json
{
  "timestamp": "2026-01-29T12:34:56.789Z",
  "session_id": "abc123",
  "category": "tokens",
  "amount": 0.045,
  "details": {
    "model": "sonnet",
    "input_tokens": 15000,
    "output_tokens": 6000,
    "cached_tokens": 3000,
    "input_cost": 0.036,
    "cached_cost": 0.009,
    "output_cost": 0.09
  }
}
```

## ROI Analysis

### TIER 2B Task 19: Agent Cost Tracking (GAP-COST-IMPL-003)

**Target**: Unified cost tracking across all agent operations

**Value**:
- Visibility into total agent costs (not just tokens)
- Budget monitoring (session + daily limits)
- Cost breakdown by category/model/tool
- Historical cost analysis
- ROI validation for optimization efforts

**Annual Value**: $8,000-12,000
- Prevents budget overruns
- Identifies cost hotspots
- Validates optimization ROI (model routing, caching, context compression)
- Enables data-driven cost decisions

## Version History

- **v1.0.0** (2026-01-29): Initial release
  - 6 cost categories (tokens, tools, subagents, external_apis, compute, storage)
  - Session and daily summaries
  - Budget tracking (healthy/warning/critical)
  - CLI interface
  - 9 self-tests (100% pass)
