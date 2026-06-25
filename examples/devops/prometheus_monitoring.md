# Example: Prometheus Monitoring Setup

## User Request

```
Настрой Prometheus для мониторинга Python приложения: метрики запросов, ошибок, latency, бизнес-метрики.
```

## Reasoning

**Domain:** DevOps (observability)
**Complexity:** Simple
**Model:** Haiku

## Response

### Python Application Instrumentation

```python
# app.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Flask, Response
import time

app = Flask(__name__)

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ACTIVE_USERS = Gauge('active_users', 'Number of active users')
ORDERS_TOTAL = Counter('orders_total', 'Total orders', ['status'])
REVENUE = Gauge('revenue_usd', 'Total revenue in USD')

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).observe(latency)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()

    return response

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/api/order', methods=['POST'])
def create_order():
    # Business logic
    order_total = 99.99
    ORDERS_TOTAL.labels(status='completed').inc()
    REVENUE.inc(order_total)
    return {'status': 'success'}
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

scrape_configs:
  - job_name: 'myapp'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['production']
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: myapp
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace

  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
```

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: application
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency (p95 > 1s)"

      - alert: LowActiveUsers
        expr: active_users < 10
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Unusually low active users"
```

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Application Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (status)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "p95 Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))"
          }
        ],
        "type": "singlestat",
        "thresholds": "0.01,0.05"
      }
    ]
  }
}
```

---

## Key Takeaways

1. **4 Golden Signals** — latency, traffic, errors, saturation
2. **Business metrics** — track revenue, orders, users
3. **Service discovery** — auto-detect Kubernetes pods
4. **Alerting** — Prometheus Alertmanager for notifications
5. **Visualization** — Grafana dashboards for analysis

**Tools:** Prometheus, Grafana, Alertmanager
**Best Practice:** Use histograms for latency, counters for events, gauges for current state
