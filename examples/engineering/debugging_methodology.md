# Few-Shot Example: Systematic Debugging Methodology

**Domain:** Engineering / Debugging
**Skill Level:** Advanced
**Pattern:** Scientific debugging approach with hypothesis testing

---

## User Query

```
My Python API is returning 500 errors intermittently. Sometimes it works, sometimes it fails. How do I debug this?
```

---

## Exemplary Response

### Debugging Methodology: Systematic Approach

#### Step 1: Reproduce the Problem

**Goal:** Make the problem predictable and repeatable.

```python
# Create a script to reproduce the issue
import requests
import time

def test_api_reliability(n=100):
    """Test API reliability over multiple requests."""
    successes = 0
    failures = 0
    errors = []

    for i in range(n):
        try:
            response = requests.post(
                "https://api.example.com/endpoint",
                json={"data": f"test-{i}"},
                timeout=5
            )
            if response.status_code == 200:
                successes += 1
            else:
                failures += 1
                errors.append({
                    "request_id": i,
                    "status_code": response.status_code,
                    "body": response.text
                })
        except requests.exceptions.RequestException as e:
            failures += 1
            errors.append({"request_id": i, "exception": str(e)})

        time.sleep(0.1)  # Avoid rate limiting

    print(f"Success rate: {successes/n*100:.1%}")
    print(f"Failures: {failures}")
    return errors

# Run reproduction test
errors = test_api_reliability(100)
```

**Observations to make:**
- Failure rate (5%? 50%?)
- Pattern (time-based? load-based? random?)
- Error messages in responses

---

#### Step 2: Gather Context & Logs

**Hypothesis generation requires data.**

```bash
# Check application logs (last 1000 lines with 500 errors)
kubectl logs deployment/api-app --tail=1000 | grep "500\|ERROR\|Exception"

# Check system metrics at time of failures
curl "http://prometheus/api/v1/query?query=rate(http_requests_total{status='500'}[5m])"

# Check resource usage
kubectl top pods -n production

# Database connection pool status
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

**Look for correlations:**
- Spike in requests → Thread pool exhaustion?
- Memory usage spikes → Memory leak?
- Database connection count high → Connection pool exhaustion?

---

#### Step 3: Form Hypotheses (Most Likely → Least Likely)

Based on "intermittent 500 errors," common hypotheses:

1. **🎯 Database connection pool exhaustion**
   - Symptom: Works when pool has connections, fails when exhausted
   - Test: Check connection pool size vs concurrent requests

2. **🎯 Race condition in shared state**
   - Symptom: Only fails under concurrent load
   - Test: Single-threaded vs multi-threaded behavior

3. **🎯 External service timeout**
   - Symptom: Fails when downstream service is slow
   - Test: Check external service latency metrics

4. **Unhandled exception in edge case**
   - Symptom: Specific input triggers error
   - Test: Review error logs for patterns in request data

---

#### Step 4: Test Hypotheses Systematically

**Hypothesis 1: Database Connection Pool Exhaustion**

```python
# Check connection pool configuration
# config.py
SQLALCHEMY_DATABASE_URI = "postgresql://..."
SQLALCHEMY_POOL_SIZE = 10          # Current
SQLALCHEMY_MAX_OVERFLOW = 20       # Current

# Add monitoring
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    print(f"[POOL] Connection created: {id(dbapi_conn)}")

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    print(f"[POOL] Connection checked out: {id(dbapi_conn)}")

@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    print(f"[POOL] Connection returned: {id(dbapi_conn)}")

# Test under load
import concurrent.futures

def make_request():
    response = requests.post("http://api/endpoint", json={"test": 1})
    return response.status_code

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(lambda _: make_request(), range(100)))

failure_rate = results.count(500) / len(results)
print(f"Failure rate with 50 concurrent requests: {failure_rate:.1%}")
```

**Result:** If failure rate increases with concurrency → Pool exhaustion confirmed.

**Fix:**
```python
# Increase pool size
SQLALCHEMY_POOL_SIZE = 30
SQLALCHEMY_MAX_OVERFLOW = 50
SQLALCHEMY_POOL_TIMEOUT = 30  # Wait 30s for connection

# Add connection return discipline
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()  # Ensure connections returned
```

---

**Hypothesis 2: Race Condition**

```python
# Add thread-safety to suspicious code
# BEFORE (vulnerable to race condition)
class Cache:
    def __init__(self):
        self._cache = {}

    def get_or_compute(self, key, compute_fn):
        if key not in self._cache:
            self._cache[key] = compute_fn()  # ⚠️ Race condition!
        return self._cache[key]

# AFTER (thread-safe)
import threading

class Cache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key, compute_fn):
        with self._lock:
            if key not in self._cache:
                self._cache[key] = compute_fn()
            return self._cache[key]

# Or use thread-safe data structure
from cachetools import TTLCache
self._cache = TTLCache(maxsize=1000, ttl=300)  # Thread-safe
```

**Test:**
```python
# Stress test with concurrent access
import concurrent.futures

cache = Cache()

def concurrent_access(i):
    return cache.get_or_compute(f"key-{i % 10}", lambda: time.sleep(0.1) or i)

with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
    results = list(executor.map(concurrent_access, range(1000)))

# Check for duplicates (indicates race condition)
if len(results) != len(set(results)):
    print("⚠️ Race condition detected!")
```

---

#### Step 5: Implement Fix & Verify

**After implementing fix (e.g., increasing pool size):**

```python
# Regression test
def test_high_concurrency():
    """Ensure 500 errors don't occur under high load."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        results = list(executor.map(lambda _: make_request(), range(1000)))

    failure_rate = results.count(500) / len(results)
    assert failure_rate == 0, f"Still seeing {failure_rate:.1%} failures!"

# Monitoring alert
# prometheus alert rule
alert: HighAPIErrorRate
expr: rate(http_requests_total{status="500"}[5m]) > 0.01
for: 5m
annotations:
  summary: "API error rate > 1% for 5 minutes"
```

---

#### Step 6: Document Root Cause

```markdown
## Incident Report: Intermittent 500 Errors

**Date:** 2026-01-22
**Duration:** 3 days (Jan 19-22)
**Severity:** P1 (Production impacting)

### Root Cause
Database connection pool exhaustion due to insufficient pool size (10 connections)
combined with increased traffic (+50% QPS over past week).

### Timeline
- Jan 19: User reports intermittent 500 errors
- Jan 20: Reproduced issue under load (15% failure rate at 50 QPS)
- Jan 21: Identified pool exhaustion via connection monitoring
- Jan 22: Increased pool size to 30, deployed, verified fix

### Impact
- ~10,000 requests returned 500 errors
- 15% error rate during peak hours
- No data loss or corruption

### Fix
- Increased SQLALCHEMY_POOL_SIZE from 10 to 30
- Added connection pool monitoring
- Added Prometheus alert for high error rates

### Prevention
- Implement load testing before production deployment
- Add connection pool metrics to dashboards
- Document connection pool sizing guidelines
```

---

## Why This Is A Good Example

✅ **Systematic approach** — Reproduce → Gather data → Hypothesize → Test → Fix
✅ **Scientific method** — Evidence-based, not guesswork
✅ **Prioritized hypotheses** — Most likely causes first
✅ **Concrete tests** — Reproducible tests for each hypothesis
✅ **Monitoring integration** — Prevent future occurrences
✅ **Documentation** — Root cause analysis for future reference

---

## Key Patterns

1. **Reproduce first** — Can't fix what you can't reproduce
2. **Gather data** — Logs, metrics, traces before hypothesizing
3. **Prioritize hypotheses** — Most likely → least likely
4. **Test scientifically** — One variable at a time
5. **Verify fix** — Regression tests + monitoring
6. **Document** — RCA for institutional knowledge

---

**Tags:** #debugging #troubleshooting #root-cause-analysis #systematic-debugging
**Version:** 1.0.0
**Last Updated:** 2026-01-22
