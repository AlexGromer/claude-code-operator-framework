# Example: Metrics Dashboard Implementation

**Domain:** Maturity Model
**Task Type:** Implementation
**Complexity:** Medium
**Skills:** Python, data visualization, metrics tracking

---

## Scenario

User wants to create a unified metrics dashboard to visualize agent performance, cost, and quality metrics from the evaluation framework.

---

## User Request

```
Create a web dashboard to visualize metrics from ~/.claude/evaluation/data/*.jsonl files. Show:
- Hallucination rate over time
- Cost breakdown by category
- Agent effectiveness scores
- Task completion rates
- Security test results

Use lightweight framework (no heavy dependencies).
```

---

## Claude Response

### Terminology Glossary

| Term | Definition |
|------|------------|
| **JSONL** | JSON Lines — one JSON object per line |
| **Hallucination rate** | Percentage of responses with factual errors |
| **Agent effectiveness** | Composite score: task completion × quality |
| **Security test results** | Pass/fail rate for prompt injection detection |

---

### Understanding

**Requirements:**
1. Read multiple JSONL files from evaluation framework
2. Aggregate metrics across time periods
3. Create visualizations (charts/graphs)
4. Lightweight (avoid Flask/Django overhead)
5. Serve dashboard locally

**Data sources:**
- `~/.claude/evaluation/data/hallucinations.jsonl`
- `~/.claude/evaluation/data/costs.jsonl`
- `~/.claude/evaluation/data/agent_metrics.jsonl`
- `~/.claude/evaluation/data/task_completion.jsonl`
- `~/.claude/evaluation/data/security_eval.jsonl`

---

### Execution Plan

```
1. Choose framework → http.server + Chart.js (zero dependencies)
2. Create data aggregation script → Python
3. Generate HTML dashboard → Single-file HTML
4. Serve dashboard → python -m http.server
5. Add refresh mechanism → Auto-reload every 60s
```

**Approval:** Awaiting confirmation to proceed.

---

### Implementation

#### Step 1: Data Aggregation Script

```python
#!/usr/bin/env python3
"""
Metrics aggregator for Claude Code evaluation data.
Reads JSONL files and generates JSON for dashboard.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = Path.home() / ".claude/evaluation/data"
OUTPUT_FILE = Path("/tmp/metrics_dashboard_data.json")

def load_jsonl(file_path):
    """Load JSONL file and return list of records."""
    if not file_path.exists():
        return []
    with open(file_path, 'r') as f:
        return [json.loads(line) for line in f if line.strip()]

def aggregate_hallucinations():
    """Aggregate hallucination rate over time."""
    records = load_jsonl(DATA_DIR / "hallucinations.jsonl")

    # Group by date
    by_date = defaultdict(lambda: {"total": 0, "hallucinations": 0})
    for record in records:
        date = record.get("timestamp", "")[:10]  # YYYY-MM-DD
        by_date[date]["total"] += 1
        if record.get("is_hallucination"):
            by_date[date]["hallucinations"] += 1

    # Calculate rates
    return [
        {
            "date": date,
            "rate": (data["hallucinations"] / data["total"] * 100) if data["total"] > 0 else 0,
            "count": data["hallucinations"]
        }
        for date, data in sorted(by_date.items())
    ]

def aggregate_costs():
    """Aggregate costs by category."""
    records = load_jsonl(DATA_DIR / "costs.jsonl")

    by_category = defaultdict(float)
    for record in records:
        category = record.get("category", "unknown")
        cost = record.get("cost", 0)
        by_category[category] += cost

    return [
        {"category": cat, "cost": cost}
        for cat, cost in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    ]

def aggregate_agent_effectiveness():
    """Aggregate agent effectiveness scores."""
    records = load_jsonl(DATA_DIR / "agent_metrics.jsonl")

    by_date = defaultdict(list)
    for record in records:
        date = record.get("timestamp", "")[:10]
        score = record.get("effectiveness_score", 0)
        by_date[date].append(score)

    return [
        {
            "date": date,
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores)
        }
        for date, scores in sorted(by_date.items())
    ]

def aggregate_task_completion():
    """Aggregate task completion rates."""
    records = load_jsonl(DATA_DIR / "task_completion.jsonl")

    by_date = defaultdict(lambda: {"total": 0, "completed": 0})
    for record in records:
        date = record.get("timestamp", "")[:10]
        by_date[date]["total"] += 1
        if record.get("status") == "completed":
            by_date[date]["completed"] += 1

    return [
        {
            "date": date,
            "completion_rate": (data["completed"] / data["total"] * 100) if data["total"] > 0 else 0,
            "completed": data["completed"],
            "total": data["total"]
        }
        for date, data in sorted(by_date.items())
    ]

def aggregate_security():
    """Aggregate security test results."""
    records = load_jsonl(DATA_DIR / "security_eval.jsonl")

    by_category = defaultdict(lambda: {"total": 0, "passed": 0})
    for record in records:
        category = record.get("attack_category", "unknown")
        by_category[category]["total"] += 1
        if record.get("blocked"):
            by_category[category]["passed"] += 1

    return [
        {
            "category": cat,
            "pass_rate": (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0,
            "passed": data["passed"],
            "total": data["total"]
        }
        for cat, data in sorted(by_category.items())
    ]

def generate_dashboard_data():
    """Generate all dashboard data."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "hallucinations": aggregate_hallucinations(),
        "costs": aggregate_costs(),
        "agent_effectiveness": aggregate_agent_effectiveness(),
        "task_completion": aggregate_task_completion(),
        "security": aggregate_security()
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Dashboard data generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_dashboard_data()
```

#### Step 2: Dashboard HTML

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e1e1e;
            color: #e0e0e0;
            padding: 20px;
        }
        .header {
            background: #2d2d2d;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        h1 { color: #4fc3f7; margin-bottom: 10px; }
        .timestamp { color: #999; font-size: 14px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }
        .card {
            background: #2d2d2d;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .card h2 {
            color: #81c784;
            margin-bottom: 15px;
            font-size: 18px;
        }
        canvas { max-height: 300px; }
        .refresh-btn {
            background: #4fc3f7;
            color: #1e1e1e;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .refresh-btn:hover { background: #29b6f6; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Claude Code Metrics Dashboard</h1>
        <div class="timestamp">Generated: <span id="timestamp">—</span></div>
        <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Hallucination Rate Over Time</h2>
            <canvas id="hallucinationChart"></canvas>
        </div>

        <div class="card">
            <h2>Cost Breakdown by Category</h2>
            <canvas id="costChart"></canvas>
        </div>

        <div class="card">
            <h2>Agent Effectiveness Scores</h2>
            <canvas id="effectivenessChart"></canvas>
        </div>

        <div class="card">
            <h2>Task Completion Rate</h2>
            <canvas id="completionChart"></canvas>
        </div>

        <div class="card">
            <h2>Security Test Results</h2>
            <canvas id="securityChart"></canvas>
        </div>
    </div>

    <script>
        let charts = {};

        async function loadData() {
            const response = await fetch('/metrics_dashboard_data.json');
            const data = await response.json();

            document.getElementById('timestamp').textContent = new Date(data.generated_at).toLocaleString();

            // Hallucination chart
            if (charts.hallucination) charts.hallucination.destroy();
            charts.hallucination = new Chart(document.getElementById('hallucinationChart'), {
                type: 'line',
                data: {
                    labels: data.hallucinations.map(d => d.date),
                    datasets: [{
                        label: 'Hallucination Rate (%)',
                        data: data.hallucinations.map(d => d.rate),
                        borderColor: '#f44336',
                        backgroundColor: 'rgba(244, 67, 54, 0.1)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { labels: { color: '#e0e0e0' } } },
                    scales: {
                        y: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } },
                        x: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } }
                    }
                }
            });

            // Cost chart
            if (charts.cost) charts.cost.destroy();
            charts.cost = new Chart(document.getElementById('costChart'), {
                type: 'bar',
                data: {
                    labels: data.costs.map(d => d.category),
                    datasets: [{
                        label: 'Cost ($)',
                        data: data.costs.map(d => d.cost),
                        backgroundColor: '#4fc3f7'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { labels: { color: '#e0e0e0' } } },
                    scales: {
                        y: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } },
                        x: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } }
                    }
                }
            });

            // Effectiveness chart
            if (charts.effectiveness) charts.effectiveness.destroy();
            charts.effectiveness = new Chart(document.getElementById('effectivenessChart'), {
                type: 'line',
                data: {
                    labels: data.agent_effectiveness.map(d => d.date),
                    datasets: [{
                        label: 'Avg Effectiveness',
                        data: data.agent_effectiveness.map(d => d.avg_score),
                        borderColor: '#81c784',
                        backgroundColor: 'rgba(129, 199, 132, 0.1)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { labels: { color: '#e0e0e0' } } },
                    scales: {
                        y: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } },
                        x: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } }
                    }
                }
            });

            // Completion chart
            if (charts.completion) charts.completion.destroy();
            charts.completion = new Chart(document.getElementById('completionChart'), {
                type: 'line',
                data: {
                    labels: data.task_completion.map(d => d.date),
                    datasets: [{
                        label: 'Completion Rate (%)',
                        data: data.task_completion.map(d => d.completion_rate),
                        borderColor: '#ffb74d',
                        backgroundColor: 'rgba(255, 183, 77, 0.1)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { labels: { color: '#e0e0e0' } } },
                    scales: {
                        y: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } },
                        x: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } }
                    }
                }
            });

            // Security chart
            if (charts.security) charts.security.destroy();
            charts.security = new Chart(document.getElementById('securityChart'), {
                type: 'bar',
                data: {
                    labels: data.security.map(d => d.category),
                    datasets: [{
                        label: 'Pass Rate (%)',
                        data: data.security.map(d => d.pass_rate),
                        backgroundColor: '#9575cd'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { labels: { color: '#e0e0e0' } } },
                    scales: {
                        y: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' }, max: 100 },
                        x: { ticks: { color: '#e0e0e0', maxRotation: 45, minRotation: 45 }, grid: { color: '#444' } }
                    }
                }
            });
        }

        // Auto-refresh every 60 seconds
        setInterval(loadData, 60000);
        loadData();
    </script>
</body>
</html>
```

#### Step 3: Serve Dashboard

```bash
# Generate data
python ~/.claude/tools/metrics_dashboard.py

# Serve dashboard
cd /tmp
python -m http.server 8080

# Open browser
xdg-open http://localhost:8080/metrics_dashboard.html
```

---

### Summary

**Created:**
1. `~/.claude/tools/metrics_dashboard.py` — Data aggregation script
2. `/tmp/metrics_dashboard.html` — Dashboard HTML
3. HTTP server serving on port 8080

**Key Decisions:**
- Used Chart.js (CDN) instead of heavy framework
- Single-file HTML (no build step)
- Auto-refresh every 60s
- Dark theme for readability

**Next Steps:**
- Add authentication if exposing externally
- Create systemd service for auto-start
- Add export to PNG/PDF functionality

---

## Lessons Learned

1. **Lightweight frameworks** reduce setup complexity
2. **JSONL format** makes incremental updates easy
3. **Chart.js** provides professional visualizations with minimal code
4. **Auto-refresh** keeps dashboard current without manual intervention
5. **Dark theme** improves readability for long-term monitoring

---

**Tags:** `maturity-model` `metrics` `dashboard` `visualization` `python` `chartjs`
