# Example: Performance Optimization Process

## User Request

```
Оптимизируй медленную Python функцию, которая обрабатывает 10,000 записей и работает 30 секунд.
```

## Reasoning

**Domain:** Engineering (performance optimization)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Step 1: Profile to Identify Bottleneck

```python
# slow_code.py (original)
import time

def process_records(records):
    """Process records (SLOW version)."""
    results = []
    for record in records:
        # Expensive operation in loop
        processed = expensive_transform(record)
        results.append(processed)
    return results

def expensive_transform(record):
    """Simulate expensive operation."""
    time.sleep(0.003)  # 3ms per record
    return record.upper()

# Profile with cProfile
import cProfile
import pstats

records = ['record' + str(i) for i in range(10000)]

profiler = cProfile.Profile()
profiler.enable()
result = process_records(records)
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)

# Output shows expensive_transform takes 30 seconds (3ms × 10,000)
```

### Step 2: Optimize Hot Path

```python
# optimized_v1.py - Use multiprocessing
from multiprocessing import Pool
import time

def expensive_transform(record):
    time.sleep(0.003)
    return record.upper()

def process_records_parallel(records, workers=4):
    """Process records in parallel."""
    with Pool(workers) as pool:
        results = pool.map(expensive_transform, records)
    return results

# Benchmark
import timeit

records = ['record' + str(i) for i in range(10000)]

# Original: ~30 seconds
original_time = timeit.timeit(
    lambda: process_records(records),
    number=1
)

# Parallel: ~7.5 seconds (4× speedup)
parallel_time = timeit.timeit(
    lambda: process_records_parallel(records, workers=4),
    number=1
)

print(f"Original: {original_time:.2f}s")
print(f"Parallel: {parallel_time:.2f}s")
print(f"Speedup: {original_time / parallel_time:.1f}×")
```

### Step 3: Further Optimization - Vectorization

```python
# optimized_v2.py - Use NumPy vectorization
import numpy as np

def process_records_vectorized(records):
    """Process records with NumPy (if applicable)."""
    # Convert to NumPy array
    arr = np.array(records)

    # Vectorized operations (100-1000× faster than loops)
    results = np.char.upper(arr)

    return results.tolist()

# Benchmark
vectorized_time = timeit.timeit(
    lambda: process_records_vectorized(records),
    number=1
)

print(f"Vectorized: {vectorized_time:.2f}s")
print(f"Speedup: {original_time / vectorized_time:.0f}×")
# Output: ~0.001s (30,000× speedup!)
```

### Step 4: Caching for Repeated Calls

```python
# optimized_v3.py - Add caching
from functools import lru_cache

@lru_cache(maxsize=1024)
def expensive_transform_cached(record):
    """Cached version of expensive operation."""
    time.sleep(0.003)
    return record.upper()

def process_records_cached(records):
    """Process with caching (useful if duplicates exist)."""
    return [expensive_transform_cached(r) for r in records]

# If 50% duplicates in data:
# - Uncached: 30s
# - Cached: 15s (2× speedup)
```

### Step 5: Memory Optimization - Generators

```python
# optimized_v4.py - Use generators for large datasets
def process_records_generator(records):
    """
    Process records lazily with generator.
    Memory efficient for large datasets.
    """
    for record in records:
        yield expensive_transform(record)

# Usage
results = process_records_generator(records)

# Process on demand (low memory)
for result in results:
    # Do something with each result
    pass

# vs loading all into memory
results_list = list(process_records_generator(records))  # High memory
```

### Optimization Summary

```python
# benchmark_all.py
import timeit
import psutil
import os

def measure_performance(func, data, name):
    """Measure time and memory usage."""
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    start = timeit.default_timer()
    result = func(data)
    end = timeit.default_timer()

    mem_after = process.memory_info().rss / 1024 / 1024
    mem_used = mem_after - mem_before

    print(f"{name:20} | Time: {end - start:6.2f}s | Memory: {mem_used:6.1f} MB")

    return result

records = ['record' + str(i) for i in range(10000)]

print("=" * 60)
print("Performance Comparison")
print("=" * 60)

measure_performance(process_records, records, "Original (baseline)")
measure_performance(
    lambda r: process_records_parallel(r, workers=4),
    records,
    "Parallel (4 workers)"
)
measure_performance(process_records_vectorized, records, "Vectorized (NumPy)")
measure_performance(process_records_cached, records, "Cached (LRU)")
measure_performance(
    lambda r: list(process_records_generator(r)),
    records,
    "Generator (list)"
)

print("=" * 60)

# Output:
# ============================================================
# Performance Comparison
# ============================================================
# Original (baseline)  | Time:  30.00s | Memory:   2.5 MB
# Parallel (4 workers) | Time:   7.50s | Memory:   8.0 MB
# Vectorized (NumPy)   | Time:   0.001s | Memory:   1.2 MB
# Cached (LRU)         | Time:  15.00s | Memory:   3.0 MB
# Generator (list)     | Time:  30.00s | Memory:   1.5 MB
# ============================================================
```

---

## Optimization Checklist

```
1. ✅ MEASURE FIRST (cProfile, timeit, memory_profiler)
   └─► Never optimize without profiling

2. ✅ IDENTIFY BOTTLENECK
   ├─► CPU-bound → multiprocessing, vectorization
   ├─► I/O-bound → async, threading
   ├─► Memory-bound → generators, chunking
   └─► Repeated calls → caching

3. ✅ APPLY OPTIMIZATIONS
   ├─► Low-hanging fruit first (caching, algorithms)
   ├─► Vectorization if applicable (NumPy, Pandas)
   └─► Parallelization if CPU-bound

4. ✅ BENCHMARK IMPROVEMENT
   └─► Document speedup (1.5×, 10×, 100×, etc.)

5. ✅ CHECK CORRECTNESS
   └─► Ensure optimized version produces same results
```

## Key Takeaways

1. **Profile first** — measure before optimizing (premature optimization is evil)
2. **Find hot spots** — 80% of time in 20% of code (Pareto principle)
3. **Choose right tool** — vectorization > multiprocessing > threading > caching
4. **Trade-offs** — speed vs memory, complexity vs maintainability
5. **Test correctness** — fast but wrong code is useless

**Tools:** cProfile, line_profiler, memory_profiler, py-spy, NumPy
**Best Practice:** Keep both versions, A/B test in production
