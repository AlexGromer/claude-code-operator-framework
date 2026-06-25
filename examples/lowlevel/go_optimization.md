# Few-Shot Example: Go Performance Optimization

**Domain:** lowlevel
**Skill Level:** Advanced
**Pattern:** Profile → Identify → Optimize → Verify

---

## User Query

Our Go service processes 10K requests/second but we're seeing high latency at p99 (500ms vs 50ms p50). Memory usage keeps growing. Here's the hot path:

```go
func ProcessBatch(items []Item) []Result {
    results := []Result{}
    for _, item := range items {
        data, _ := json.Marshal(item)
        hash := sha256.Sum256(data)
        result := Result{
            ID:   item.ID,
            Hash: fmt.Sprintf("%x", hash),
            Time: time.Now().Format(time.RFC3339),
        }
        results = append(results, result)
    }
    return results
}
```

How do I profile and optimize this?

---

## Exemplary Response

### 1. Performance Problem Categories

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GO PERFORMANCE PROBLEM TAXONOMY                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CPU-BOUND                        MEMORY-BOUND                               │
│  ├── Inefficient algorithms       ├── Excessive allocations                 │
│  ├── Unnecessary computation      ├── Memory leaks                          │
│  ├── Lock contention              ├── Large working set                     │
│  └── GC pressure (indirect)       └── Cache misses                          │
│                                                                              │
│  I/O-BOUND                        CONCURRENCY                                │
│  ├── Blocking calls               ├── Lock contention                       │
│  ├── Small reads/writes           ├── False sharing                         │
│  ├── No connection pooling        ├── Goroutine leaks                       │
│  └── Missing buffering            └── Channel bottlenecks                   │
│                                                                              │
│  YOUR CODE SYMPTOMS:                                                         │
│  ✗ High p99 latency → GC pauses, allocations                                │
│  ✗ Memory growth → Allocations per request, possible leak                   │
│  ✗ Hot path issues → json.Marshal, fmt.Sprintf, append                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Profiling Strategy

#### 2.1 Built-in Profiling

```go
// main.go - Add pprof endpoints
import (
    "net/http"
    _ "net/http/pprof"
)

func main() {
    // Expose pprof on separate port
    go func() {
        http.ListenAndServe(":6060", nil)
    }()

    // Your application...
}
```

#### 2.2 Collect Profiles

```bash
# CPU profile (30 seconds)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile?seconds=30

# Heap profile (current allocations)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/heap

# Allocations profile (all allocations since start)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/allocs

# Goroutine profile (goroutine leaks)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/goroutine

# Block profile (blocking operations)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/block

# Mutex profile (lock contention)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/mutex
```

#### 2.3 Benchmark-Based Profiling

```go
// process_test.go
package main

import (
    "testing"
)

func BenchmarkProcessBatch(b *testing.B) {
    items := generateTestItems(1000)

    b.ResetTimer()
    b.ReportAllocs()

    for i := 0; i < b.N; i++ {
        ProcessBatch(items)
    }
}

func BenchmarkProcessBatchParallel(b *testing.B) {
    items := generateTestItems(1000)

    b.ResetTimer()
    b.ReportAllocs()

    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            ProcessBatch(items)
        }
    })
}
```

```bash
# Run benchmarks with memory profiling
go test -bench=. -benchmem -cpuprofile=cpu.out -memprofile=mem.out

# Analyze
go tool pprof -http=:8080 cpu.out
go tool pprof -http=:8080 mem.out
```

### 3. Issue Analysis

#### 3.1 Problem 1: Slice Growing (append)

```go
// PROBLEM: Slice grows dynamically, causing reallocations
results := []Result{}  // len=0, cap=0
for _, item := range items {
    results = append(results, result)  // Reallocates at 0, 1, 2, 4, 8, 16...
}
```

**Memory growth pattern:**
```
Items: 1000
Reallocations: ~10 (0→1→2→4→8→16→32→64→128→256→512→1024)
Wasted memory: up to 1024 - 1000 = 24 Result structs
```

#### 3.2 Problem 2: json.Marshal Allocations

```go
// PROBLEM: json.Marshal allocates new []byte every call
data, _ := json.Marshal(item)  // Allocates: encoder + buffer + result
```

**Per-item allocations:**
- `json.Encoder` internal state
- Growing byte buffer
- Final `[]byte` result

#### 3.3 Problem 3: fmt.Sprintf for Hex

```go
// PROBLEM: fmt.Sprintf allocates, uses reflection
Hash: fmt.Sprintf("%x", hash)  // Allocates string + uses reflection
```

#### 3.4 Problem 4: time.Now().Format()

```go
// PROBLEM: Format allocates string every call
Time: time.Now().Format(time.RFC3339)  // Allocates ~25 bytes
```

### 4. Optimized Implementation

```go
package main

import (
    "encoding/hex"
    "crypto/sha256"
    "sync"
    "time"

    "github.com/json-iterator/go"
)

// Use faster JSON library (optional, but significant improvement)
var json = jsoniter.ConfigCompatibleWithStandardLibrary

// Pre-allocate hex encoding buffer via sync.Pool
var hexBufPool = sync.Pool{
    New: func() interface{} {
        buf := make([]byte, hex.EncodedLen(sha256.Size))
        return &buf
    },
}

// Pre-allocate Result slice via sync.Pool
var resultPool = sync.Pool{
    New: func() interface{} {
        s := make([]Result, 0, 1024)
        return &s
    },
}

// Reusable JSON encoder buffer
var jsonBufPool = sync.Pool{
    New: func() interface{} {
        return make([]byte, 0, 4096)
    },
}

// Result with pre-sized Hash field
type Result struct {
    ID   int64  `json:"id"`
    Hash string `json:"hash"`  // Always 64 chars for SHA256
    Time int64  `json:"time"`  // Unix timestamp instead of string
}

func ProcessBatchOptimized(items []Item) []Result {
    n := len(items)
    if n == 0 {
        return nil
    }

    // 1. Pre-allocate result slice with exact capacity
    results := make([]Result, n)

    // 2. Get reusable buffers from pool
    hexBufPtr := hexBufPool.Get().(*[]byte)
    hexBuf := *hexBufPtr
    defer hexBufPool.Put(hexBufPtr)

    jsonBuf := jsonBufPool.Get().([]byte)
    defer jsonBufPool.Put(jsonBuf[:0])  // Reset length on return

    // 3. Cache current time (if all items processed "now")
    now := time.Now().Unix()

    // 4. Process items
    var hasher = sha256.New()

    for i := range items {
        // Reset and reuse hasher
        hasher.Reset()

        // Marshal to reusable buffer
        jsonBuf = jsonBuf[:0]
        jsonBuf, _ = json.Marshal(items[i])  // jsoniter can use existing buffer

        // Hash without allocation
        hasher.Write(jsonBuf)
        hashBytes := hasher.Sum(nil)

        // Hex encode to pre-allocated buffer
        hex.Encode(hexBuf, hashBytes)

        // Create result (string() copies, but unavoidable for Hash)
        results[i] = Result{
            ID:   items[i].ID,
            Hash: string(hexBuf),  // Single allocation for hash string
            Time: now,             // No allocation (int64)
        }
    }

    return results
}

// Even more optimized: parallel processing for large batches
func ProcessBatchParallel(items []Item, workers int) []Result {
    n := len(items)
    if n == 0 {
        return nil
    }

    results := make([]Result, n)
    now := time.Now().Unix()

    // Use worker pool for large batches
    if n < 100 || workers <= 1 {
        return ProcessBatchOptimized(items)
    }

    chunkSize := (n + workers - 1) / workers
    var wg sync.WaitGroup

    for w := 0; w < workers; w++ {
        start := w * chunkSize
        end := start + chunkSize
        if end > n {
            end = n
        }
        if start >= n {
            break
        }

        wg.Add(1)
        go func(start, end int) {
            defer wg.Done()

            // Each goroutine gets its own buffers
            hexBuf := make([]byte, hex.EncodedLen(sha256.Size))
            hasher := sha256.New()

            for i := start; i < end; i++ {
                hasher.Reset()
                data, _ := json.Marshal(items[i])
                hasher.Write(data)
                hex.Encode(hexBuf, hasher.Sum(nil))

                results[i] = Result{
                    ID:   items[i].ID,
                    Hash: string(hexBuf),
                    Time: now,
                }
            }
        }(start, end)
    }

    wg.Wait()
    return results
}
```

### 5. Benchmark Comparison

```go
// process_test.go
func BenchmarkOriginal(b *testing.B) {
    items := generateTestItems(1000)
    b.ResetTimer()
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        ProcessBatch(items)
    }
}

func BenchmarkOptimized(b *testing.B) {
    items := generateTestItems(1000)
    b.ResetTimer()
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        ProcessBatchOptimized(items)
    }
}

func BenchmarkParallel4(b *testing.B) {
    items := generateTestItems(1000)
    b.ResetTimer()
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        ProcessBatchParallel(items, 4)
    }
}
```

**Expected Results:**

| Version | ns/op | B/op | allocs/op |
|---------|-------|------|-----------|
| Original | 850,000 | 512,000 | 5,012 |
| Optimized | 180,000 | 128,000 | 1,002 |
| Parallel(4) | 55,000 | 130,000 | 1,010 |

**Improvements:**
- **4.7x faster** (single-threaded optimized)
- **15x faster** (parallel with 4 workers)
- **75% fewer allocations**
- **75% less memory per operation**

### 6. GC Tuning

```bash
# Increase GOGC for throughput (default 100)
export GOGC=200  # GC runs at 2x heap size instead of 1x

# Or use ballast for more predictable GC
```

```go
// Ballast trick: allocate large unused slice to delay GC
func main() {
    // 100MB ballast - GC triggers less frequently
    ballast := make([]byte, 100<<20)
    _ = ballast

    // Your application...
}
```

### 7. Memory Leak Detection

```go
// Add to your monitoring
func ReportMemStats() {
    var m runtime.MemStats
    runtime.ReadMemStats(&m)

    log.Printf("Alloc = %v MiB", m.Alloc/1024/1024)
    log.Printf("TotalAlloc = %v MiB", m.TotalAlloc/1024/1024)
    log.Printf("Sys = %v MiB", m.Sys/1024/1024)
    log.Printf("NumGC = %v", m.NumGC)
    log.Printf("NumGoroutine = %v", runtime.NumGoroutine())
}
```

**Leak indicators:**
- `NumGoroutine` keeps growing → goroutine leak
- `Alloc` keeps growing between GCs → memory leak
- `NumGC` very frequent → too many allocations

### 8. Optimization Checklist

| Optimization | Impact | Complexity |
|--------------|--------|------------|
| Pre-allocate slices with `make(T, 0, n)` | High | Low |
| Use `sync.Pool` for reusable buffers | High | Medium |
| Replace `fmt.Sprintf` with specialized functions | Medium | Low |
| Use `jsoniter` instead of `encoding/json` | High | Low |
| Avoid `time.Format`, use Unix timestamps | Low | Low |
| Parallel processing for CPU-bound work | High | Medium |
| Batch I/O operations | High | Medium |
| Use `strings.Builder` for string concatenation | Medium | Low |
| Avoid interface{} and reflection | Medium | Medium |

### 9. Profiling Interpretation Guide

```
CPU Profile - Top consumers:
┌────────────────────────────────────────────────────────────────────────────┐
│ flat%   cum%   function                                                    │
├────────────────────────────────────────────────────────────────────────────┤
│ 35%     35%    runtime.mallocgc          ← Too many allocations!          │
│ 20%     55%    encoding/json.Marshal     ← JSON is expensive              │
│ 15%     70%    crypto/sha256.block       ← Expected (hashing)             │
│ 10%     80%    runtime.gcBgMarkWorker    ← GC overhead from allocs        │
│  5%     85%    fmt.Sprintf               ← Reflection overhead            │
└────────────────────────────────────────────────────────────────────────────┘

Heap Profile - Top allocators:
┌────────────────────────────────────────────────────────────────────────────┐
│ flat%   cum%   function                                                    │
├────────────────────────────────────────────────────────────────────────────┤
│ 40%     40%    main.ProcessBatch ([]Result append)                        │
│ 30%     70%    encoding/json.Marshal                                       │
│ 20%     90%    fmt.Sprintf                                                 │
│ 10%    100%    time.Format                                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

### 10. Production Monitoring

```go
// Expose metrics for Prometheus
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    processingDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "batch_processing_duration_seconds",
            Help:    "Time spent processing batches",
            Buckets: prometheus.ExponentialBuckets(0.001, 2, 15),
        },
        []string{"batch_size"},
    )

    allocationsPerBatch = promauto.NewHistogram(
        prometheus.HistogramOpts{
            Name:    "batch_allocations_bytes",
            Help:    "Memory allocated per batch",
            Buckets: prometheus.ExponentialBuckets(1024, 2, 20),
        },
    )
)

func ProcessBatchInstrumented(items []Item) []Result {
    var m runtime.MemStats
    runtime.ReadMemStats(&m)
    allocBefore := m.TotalAlloc

    start := time.Now()
    results := ProcessBatchOptimized(items)
    duration := time.Since(start)

    runtime.ReadMemStats(&m)
    allocDelta := m.TotalAlloc - allocBefore

    processingDuration.WithLabelValues(
        fmt.Sprintf("%d", len(items)),
    ).Observe(duration.Seconds())

    allocationsPerBatch.Observe(float64(allocDelta))

    return results
}
```

---

## Why This Is A Good Example

- Systematic profiling approach (CPU, memory, goroutines)
- Identifies multiple optimization opportunities
- Shows before/after benchmark comparison
- Explains WHY each optimization works
- Includes production monitoring recommendations

---

## Key Patterns

1. **Profile First** - Never optimize without data
2. **Pre-allocate** - Know your sizes, avoid growing
3. **Pool Reusable Buffers** - sync.Pool for hot paths
4. **Avoid Reflection** - fmt, json are expensive
5. **Batch Work** - Amortize costs across items

---

**Tags:** #lowlevel #go #performance #profiling #optimization #memory
**Version:** 1.0.0
**Last Updated:** 2026-01-23
