#!/usr/bin/env python3
"""
Claude MCP Metrics Server
Version: 1.0.0

Model Context Protocol (MCP) server for metrics collection.
Provides structured tools for Claude to collect and query metrics.

To use:
1. Add to settings.json mcpServers section
2. Restart Claude Code

Tools provided:
- collect_metric: Record a metric data point
- query_metrics: Query historical metrics
- get_summary: Get metrics summary for period
- rate_response: Rate current response accuracy/hallucination
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# MCP Protocol version
MCP_VERSION = "2024-11-05"

# Paths
METRICS_FILE = Path.home() / ".claude" / "evaluation" / "data" / "metrics.jsonl"


def ensure_metrics_file():
    """Ensure metrics file and directory exist."""
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not METRICS_FILE.exists():
        METRICS_FILE.touch()


def read_metrics(days: int = 7) -> List[dict]:
    """Read metrics from JSONL file."""
    ensure_metrics_file()
    metrics = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        with open(METRICS_FILE, 'r') as f:
            for line in f:
                try:
                    metric = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(metric['timestamp'].replace('Z', '+00:00'))
                    if timestamp >= cutoff:
                        metrics.append(metric)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
    except FileNotFoundError:
        pass

    return metrics


def write_metric(metric_type: str, value: float, metadata: dict = None):
    """Write a single metric to JSONL file."""
    ensure_metrics_file()
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'metric_type': metric_type,
        'value': value,
        'metadata': metadata or {}
    }
    with open(METRICS_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')


# MCP Tool Definitions
TOOLS = [
    {
        "name": "collect_metric",
        "description": "Record a metric data point for Claude performance tracking. Use this to log accuracy, hallucinations, latency, or custom metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric_type": {
                    "type": "string",
                    "enum": ["accuracy", "hallucination", "tool_error", "latency", "cost", "custom"],
                    "description": "Type of metric to record"
                },
                "value": {
                    "type": "number",
                    "description": "Metric value. For rates (accuracy, hallucination, tool_error): 0.0-1.0. For latency: seconds. For cost: dollars."
                },
                "task_description": {
                    "type": "string",
                    "description": "Brief description of the task being measured"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes about this measurement"
                }
            },
            "required": ["metric_type", "value"]
        }
    },
    {
        "name": "query_metrics",
        "description": "Query historical metrics data. Returns metrics matching the specified criteria.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric_type": {
                    "type": "string",
                    "enum": ["accuracy", "hallucination", "tool_error", "latency", "cost", "all"],
                    "description": "Type of metrics to query"
                },
                "days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 90,
                    "default": 7,
                    "description": "Number of days to look back"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["metric_type"]
        }
    },
    {
        "name": "get_metrics_summary",
        "description": "Get summary statistics for metrics over a period. Returns mean, median, min, max, count for each metric type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 90,
                    "default": 7,
                    "description": "Number of days to summarize"
                }
            }
        }
    },
    {
        "name": "rate_response",
        "description": "Rate the current Claude response for accuracy and hallucination. Call this AFTER completing a task to self-assess quality.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "accuracy_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Self-assessed accuracy of the response (0.0 = completely wrong, 1.0 = fully correct)"
                },
                "has_hallucination": {
                    "type": "boolean",
                    "description": "Whether the response contained any fabricated/hallucinated information"
                },
                "task_description": {
                    "type": "string",
                    "description": "Brief description of what task was completed"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the accuracy assessment"
                }
            },
            "required": ["accuracy_score", "has_hallucination", "task_description"]
        }
    }
]


def handle_collect_metric(args: dict) -> dict:
    """Handle collect_metric tool call."""
    metric_type = args['metric_type']
    value = args['value']
    metadata = {
        'source': 'mcp_server',
        'task_description': args.get('task_description', ''),
        'notes': args.get('notes', '')
    }

    write_metric(metric_type, value, metadata)

    return {
        "success": True,
        "message": f"Recorded {metric_type} metric: {value}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def handle_query_metrics(args: dict) -> dict:
    """Handle query_metrics tool call."""
    metric_type = args.get('metric_type', 'all')
    days = args.get('days', 7)
    limit = args.get('limit', 20)

    metrics = read_metrics(days=days)

    if metric_type != 'all':
        metrics = [m for m in metrics if m.get('metric_type') == metric_type]

    # Sort by timestamp descending, limit results
    metrics = sorted(metrics, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]

    return {
        "count": len(metrics),
        "period_days": days,
        "metric_type": metric_type,
        "metrics": metrics
    }


def handle_get_metrics_summary(args: dict) -> dict:
    """Handle get_metrics_summary tool call."""
    days = args.get('days', 7)
    metrics = read_metrics(days=days)

    # Group by metric type
    by_type = {}
    for m in metrics:
        mt = m.get('metric_type', 'unknown')
        if mt not in by_type:
            by_type[mt] = []
        try:
            by_type[mt].append(float(m.get('value', 0)))
        except (ValueError, TypeError):
            continue

    # Calculate statistics
    summary = {}
    for mt, values in by_type.items():
        if values:
            sorted_values = sorted(values)
            n = len(values)
            summary[mt] = {
                'count': n,
                'mean': sum(values) / n,
                'median': sorted_values[n // 2] if n % 2 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2,
                'min': min(values),
                'max': max(values),
                'std': (sum((x - sum(values) / n) ** 2 for x in values) / n) ** 0.5 if n > 1 else 0
            }

    # Calculate targets status
    targets = {
        'accuracy': {'target': 0.85, 'direction': 'gte'},  # >= 85%
        'hallucination': {'target': 0.05, 'direction': 'lte'},  # <= 5%
        'tool_error': {'target': 0.10, 'direction': 'lte'}  # <= 10%
    }

    target_status = {}
    for mt, target_info in targets.items():
        if mt in summary:
            mean_value = summary[mt]['mean']
            if target_info['direction'] == 'gte':
                met = mean_value >= target_info['target']
            else:
                met = mean_value <= target_info['target']
            target_status[mt] = {
                'target': target_info['target'],
                'actual': mean_value,
                'met': met,
                'status': '✅' if met else '❌'
            }

    return {
        'period_days': days,
        'total_metrics': len(metrics),
        'summary': summary,
        'target_status': target_status
    }


def handle_rate_response(args: dict) -> dict:
    """Handle rate_response tool call."""
    accuracy = args['accuracy_score']
    has_hallucination = args['has_hallucination']
    task_description = args['task_description']
    confidence = args.get('confidence', 'medium')

    # Record accuracy metric
    write_metric('accuracy', accuracy, {
        'source': 'self_assessment',
        'task_description': task_description,
        'confidence': confidence
    })

    # Record hallucination metric
    write_metric('hallucination', 1.0 if has_hallucination else 0.0, {
        'source': 'self_assessment',
        'task_description': task_description,
        'confidence': confidence
    })

    return {
        "success": True,
        "message": f"Recorded self-assessment: accuracy={accuracy:.1%}, hallucination={'yes' if has_hallucination else 'no'}",
        "task": task_description
    }


# MCP Protocol Handlers
def handle_initialize(params: dict) -> dict:
    """Handle MCP initialize request."""
    return {
        "protocolVersion": MCP_VERSION,
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "claude-metrics-server",
            "version": "1.0.0"
        }
    }


def handle_list_tools(params: dict) -> dict:
    """Handle MCP tools/list request."""
    return {"tools": TOOLS}


def handle_call_tool(params: dict) -> dict:
    """Handle MCP tools/call request."""
    tool_name = params.get('name')
    arguments = params.get('arguments', {})

    handlers = {
        'collect_metric': handle_collect_metric,
        'query_metrics': handle_query_metrics,
        'get_metrics_summary': handle_get_metrics_summary,
        'rate_response': handle_rate_response
    }

    handler = handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        result = handler(arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": str(e)})
                }
            ],
            "isError": True
        }


def process_request(request: dict) -> dict:
    """Process a single MCP request."""
    method = request.get('method', '')
    params = request.get('params', {})
    request_id = request.get('id')

    handlers = {
        'initialize': handle_initialize,
        'tools/list': handle_list_tools,
        'tools/call': handle_call_tool
    }

    handler = handlers.get(method)
    if handler:
        result = handler(params)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method: {method}"
            }
        }


def main():
    """Main MCP server loop (stdio transport)."""
    # Ensure metrics file exists
    ensure_metrics_file()

    # Read from stdin, write to stdout (MCP stdio transport)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = process_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == '__main__':
    main()
