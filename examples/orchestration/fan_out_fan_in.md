# Few-Shot Example: Fan-Out/Fan-In Pattern

## Task
Пользователь: "Обработай 100 CSV files в ~/data/, извлеки метрики, агрегируй результаты. Используй fan-out/fan-in pattern."

## Solution

### Pattern Overview

```
                ┌─────────┐
                │Orchestr.│
                └────┬────┘
                     │ (Fan-Out)
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Agent 1  │ │Agent 2  │ │Agent N  │
   │Process  │ │Process  │ │Process  │
   │files 1-N│ │files N-M│ │files M-Z│
   └────┬────┘ └────┬────┘ └────┬────┘
        │            │            │
        │ (Write to scratchpad)  │
        └────────────┼────────────┘
                     │ (Fan-In)
                     ▼
                ┌─────────┐
                │Orchestr.│
                │Aggregate│
                └─────────┘
```

---

## Implementation

### Phase 1: Fan-Out (Orchestrator)

```python
import os
import glob
import math

# Step 1: Discover files
data_dir = os.path.expanduser("~/data")
csv_files = glob.glob(f"{data_dir}/*.csv")
total_files = len(csv_files)

print(f"Found {total_files} CSV files")

# Step 2: Determine parallelization
MAX_AGENTS = 10
files_per_agent = math.ceil(total_files / MAX_AGENTS)
num_agents = min(MAX_AGENTS, math.ceil(total_files / files_per_agent))

print(f"Spawning {num_agents} agents ({files_per_agent} files each)")

# Step 3: Split files into batches
file_batches = []
for i in range(num_agents):
    start_idx = i * files_per_agent
    end_idx = min((i + 1) * files_per_agent, total_files)
    batch = csv_files[start_idx:end_idx]
    file_batches.append(batch)

# Step 4: Create scratchpad directory
uid = os.getuid()
scratchpad = f"/tmp/claude-{uid}/data-processing/scratchpad"
os.makedirs(scratchpad, exist_ok=True)

# Step 5: Spawn subagents (FAN-OUT)
# In Claude Code, issue ONE message with multiple Task calls in parallel

for agent_id, batch in enumerate(file_batches):
    # Create batch file list
    batch_file = f"{scratchpad}/batch_{agent_id}.txt"
    with open(batch_file, 'w') as f:
        f.write('\n'.join(batch))

    # Spawn subagent
    prompt = f"""
Data Processing Task — Batch {agent_id + 1} of {num_agents}

## Input
File list: {batch_file}
Total files in batch: {len(batch)}

## Task
For each CSV file:
1. Read CSV
2. Extract metrics:
   - Row count
   - Column count
   - Numeric columns: min, max, mean, median
   - Categorical columns: unique values count
   - Missing values: count per column
3. Write metrics to JSON

## Output
Write to: {scratchpad}/metrics_{agent_id}.json

Format:
{{
  "batch_id": {agent_id},
  "files_processed": {len(batch)},
  "metrics": [
    {{
      "filename": "file1.csv",
      "rows": 1000,
      "columns": 10,
      "numeric_stats": {{}},
      "categorical_stats": {{}},
      "missing_values": {{}}
    }}
  ]
}}

## Requirements
- Handle CSV parsing errors gracefully
- Log any skipped files
- Complete even if some files fail

Begin processing batch {agent_id + 1}.
"""

    # Spawn subagent (haiku for simple data processing)
    Task(
        subagent_type="general-purpose",
        model="haiku",
        prompt=prompt
    )

print(f"✓ Spawned {num_agents} subagents")
print("⏳ Waiting for completion...")
```

---

### Phase 2: Subagent Processing

**Each subagent executes:**

```python
import pandas as pd
import json
import os

batch_id = 0  # Passed from orchestrator
batch_file = f"/tmp/claude-{os.getuid()}/data-processing/scratchpad/batch_{batch_id}.txt"
output_file = f"/tmp/claude-{os.getuid()}/data-processing/scratchpad/metrics_{batch_id}.json"

# Read file list
with open(batch_file) as f:
    files = [line.strip() for line in f]

metrics = []
errors = []

for filepath in files:
    try:
        # Read CSV
        df = pd.read_csv(filepath)

        # Extract metrics
        file_metrics = {
            "filename": os.path.basename(filepath),
            "rows": len(df),
            "columns": len(df.columns),
            "numeric_stats": {},
            "categorical_stats": {},
            "missing_values": {}
        }

        # Numeric columns
        for col in df.select_dtypes(include=['number']).columns:
            file_metrics["numeric_stats"][col] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "median": float(df[col].median())
            }

        # Categorical columns
        for col in df.select_dtypes(include=['object']).columns:
            file_metrics["categorical_stats"][col] = {
                "unique_values": int(df[col].nunique())
            }

        # Missing values
        for col in df.columns:
            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                file_metrics["missing_values"][col] = missing_count

        metrics.append(file_metrics)

    except Exception as e:
        errors.append({
            "filename": os.path.basename(filepath),
            "error": str(e)
        })

# Write output
result = {
    "batch_id": batch_id,
    "files_processed": len(metrics),
    "files_failed": len(errors),
    "metrics": metrics,
    "errors": errors
}

with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print(f"✓ Batch {batch_id}: Processed {len(metrics)} files, {len(errors)} errors")
print(f"✓ Output: {output_file}")
```

---

### Phase 3: Fan-In (Orchestrator)

```python
import json
import glob
import time

# Wait for all subagents to complete
# (In Claude Code, this happens automatically when all Task calls return)

# Step 1: Collect results from all subagents
scratchpad = f"/tmp/claude-{os.getuid()}/data-processing/scratchpad"
result_files = glob.glob(f"{scratchpad}/metrics_*.json")

print(f"✓ Collected results from {len(result_files)} agents")

# Step 2: Aggregate metrics
all_metrics = []
all_errors = []
total_files_processed = 0
total_rows = 0
total_columns_sum = 0

for result_file in result_files:
    with open(result_file) as f:
        batch_result = json.load(f)

        all_metrics.extend(batch_result['metrics'])
        all_errors.extend(batch_result.get('errors', []))
        total_files_processed += batch_result['files_processed']

        # Aggregate stats
        for metric in batch_result['metrics']:
            total_rows += metric['rows']
            total_columns_sum += metric['columns']

# Step 3: Compute global statistics
avg_rows_per_file = total_rows / total_files_processed if total_files_processed > 0 else 0
avg_columns_per_file = total_columns_sum / total_files_processed if total_files_processed > 0 else 0

# Find files with most missing values
files_by_missing = sorted(
    all_metrics,
    key=lambda x: sum(x['missing_values'].values()),
    reverse=True
)[:10]

# Step 4: Generate aggregated report
report = {
    "processing_timestamp": "2026-02-06T12:00:00Z",
    "total_files": total_files,
    "files_processed": total_files_processed,
    "files_failed": len(all_errors),
    "global_stats": {
        "total_rows": total_rows,
        "avg_rows_per_file": round(avg_rows_per_file, 2),
        "avg_columns_per_file": round(avg_columns_per_file, 2)
    },
    "top_files_by_missing_values": [
        {
            "filename": f['filename'],
            "missing_count": sum(f['missing_values'].values())
        }
        for f in files_by_missing
    ],
    "errors": all_errors
}

# Write final report
output_path = os.path.expanduser("~/data/aggregated_metrics.json")
with open(output_path, 'w') as f:
    json.dump(report, f, indent=2)

# Generate markdown summary
markdown = f"""
# Data Processing Report

**Date:** 2026-02-06
**Total Files:** {total_files}
**Processed:** {total_files_processed}
**Failed:** {len(all_errors)}

## Global Statistics

- **Total Rows:** {total_rows:,}
- **Avg Rows/File:** {avg_rows_per_file:,.2f}
- **Avg Columns/File:** {avg_columns_per_file:.2f}

## Top 10 Files by Missing Values

| Filename | Missing Values |
|----------|----------------|
"""

for f in files_by_missing[:10]:
    markdown += f"| {f['filename']} | {sum(f['missing_values'].values())} |\n"

if all_errors:
    markdown += "\n## Errors\n\n"
    for error in all_errors:
        markdown += f"- `{error['filename']}`: {error['error']}\n"

markdown_path = os.path.expanduser("~/data/DATA_PROCESSING_REPORT.md")
with open(markdown_path, 'w') as f:
    f.write(markdown)

print("=" * 60)
print("✅ Data processing complete!")
print(f"📊 Processed: {total_files_processed}/{total_files} files")
print(f"❌ Failed: {len(all_errors)} files")
print(f"📈 Total rows: {total_rows:,}")
print(f"📄 Reports:")
print(f"  - JSON: {output_path}")
print(f"  - Markdown: {markdown_path}")
print("=" * 60)
```

---

## Performance Analysis

### Scenario: 100 CSV files, 10 agents

| Metric | Value |
|--------|-------|
| **Total files** | 100 |
| **Files per agent** | 10 |
| **Agents** | 10 (parallel) |
| **Time per file (serial)** | 10 seconds |
| **Serial total time** | 1000 seconds (16.7 min) |
| **Parallel time** | 100 seconds (1.7 min) |
| **Speedup** | 10x |

### Cost Comparison

**Serial (1 agent, Sonnet):**
- 100 files × 10s = 1000s
- Cost: $0.50

**Parallel (10 agents, Haiku):**
- 10 agents × 100s = 100s total
- Cost: 10 × $0.01 = $0.10 (Haiku is cheaper)

**Savings:** 90% cost reduction + 10x faster

---

## Best Practices

### 1. Dynamic Batch Sizing

```python
# Adjust based on file sizes
small_files = [f for f in csv_files if os.path.getsize(f) < 1_000_000]  # <1MB
large_files = [f for f in csv_files if os.path.getsize(f) >= 1_000_000]

# More agents for large files
large_files_agents = 15
small_files_agents = 5
```

### 2. Error Handling

```python
# Each subagent should continue even if some files fail
try:
    process_file(filepath)
except Exception as e:
    errors.append({"file": filepath, "error": str(e)})
    continue  # Don't fail entire batch
```

### 3. Progress Monitoring

```python
# Write progress to shared file
progress_file = f"{scratchpad}/progress_{batch_id}.txt"

for i, filepath in enumerate(files):
    process_file(filepath)

    # Update progress
    with open(progress_file, 'w') as f:
        f.write(f"{i+1}/{len(files)}")
```

### 4. Result Validation

```python
# Orchestrator checks if all results arrived
expected_results = num_agents
actual_results = len(glob.glob(f"{scratchpad}/metrics_*.json"))

if actual_results < expected_results:
    print(f"⚠️ Warning: Expected {expected_results} results, got {actual_results}")
    # Retry missing batches
```

---

## When to Use Fan-Out/Fan-In

✅ **Use when:**
- Processing many independent items (files, records, URLs)
- Each item takes >5 seconds to process
- Items can be processed in any order
- Results need aggregation

❌ **Don't use when:**
- Items are interdependent (need results from others)
- Processing is too fast (<1 second per item) — overhead not worth it
- Order matters (sequential processing required)
- Single large file (can't split)

---

**Authoritative Sources:**
- Orchestration Patterns: `~/.claude/modules/13-orchestration-reference.md`
- Map-Reduce Pattern: https://en.wikipedia.org/wiki/MapReduce
