# Few-Shot Example: eBPF for System Observability

**Domain:** lowlevel
**Skill Level:** Advanced
**Pattern:** Understand → Instrument → Analyze → Optimize

---

## User Query

We're experiencing intermittent latency spikes in our production services. Traditional monitoring shows nothing obvious. How can we use eBPF to get deeper visibility into what's happening at the kernel level?

---

## Exemplary Response

### 1. eBPF Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         eBPF ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER SPACE                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Your Application    │    bpftrace/bcc     │    perf/trace-cmd      │   │
│  │                      │    (eBPF frontend)  │    (data consumer)      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                           ▲                   │
│                              │ Load eBPF program         │ Read data         │
│  ════════════════════════════│═══════════════════════════│═══════════════   │
│                              ▼                           │                   │
│  KERNEL SPACE                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   eBPF Virtual Machine                                               │   │
│  │   ┌─────────────────────────────────────────────────────────────┐    │   │
│  │   │  Verifier  →  JIT Compiler  →  eBPF Bytecode Execution     │    │   │
│  │   └─────────────────────────────────────────────────────────────┘    │   │
│  │                           │                                           │   │
│  │   ┌─────────────────────────────────────────────────────────────┐    │   │
│  │   │                    HOOK POINTS                               │    │   │
│  │   ├──────────────────────────────────────────────────────────────    │   │
│  │   │  kprobes   │ tracepoints │ uprobes  │ XDP    │ tc   │ cgroups   │   │
│  │   │  (dynamic) │ (static)    │ (user)   │ (net)  │(net) │ (process) │   │
│  │   └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │   ┌─────────────────────────────────────────────────────────────┐    │   │
│  │   │                    DATA STRUCTURES                           │    │   │
│  │   │  Maps (hash, array, ringbuf, perf_event, stack_trace, etc.) │    │   │
│  │   └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Common Latency Sources

| Source | Detection Method | eBPF Tool |
|--------|------------------|-----------|
| Syscall latency | kprobe on sys_* | funclatency |
| Disk I/O | tracepoint block:* | biolatency |
| Network I/O | kprobe tcp_* | tcplife, tcpretrans |
| Lock contention | kprobe mutex_* | lockstat |
| CPU scheduling | tracepoint sched:* | runqlat |
| Page faults | tracepoint exceptions:* | hardirqs, softirqs |
| Memory allocation | kprobe kmalloc | memleak |

### 3. Quick Diagnosis with bpftrace

#### 3.1 Installation

```bash
# Ubuntu/Debian
sudo apt install bpftrace bpfcc-tools linux-headers-$(uname -r)

# Check eBPF support
sudo bpftrace -e 'BEGIN { printf("eBPF works!\n"); exit(); }'
```

#### 3.2 One-Liners for Latency Debugging

```bash
# ═══════════════════════════════════════════════════════════════════════════
# CPU & SCHEDULING
# ═══════════════════════════════════════════════════════════════════════════

# Run queue latency (time waiting for CPU)
sudo bpftrace -e '
tracepoint:sched:sched_wakeup { @start[args->pid] = nsecs; }
tracepoint:sched:sched_switch {
    if (@start[args->next_pid]) {
        @usecs = hist((nsecs - @start[args->next_pid]) / 1000);
        delete(@start[args->next_pid]);
    }
}'

# Off-CPU time analysis (why process not running)
sudo bpftrace -e '
tracepoint:sched:sched_switch {
    if (args->prev_state == 1) {  // TASK_INTERRUPTIBLE
        @start[args->prev_pid] = nsecs;
    }
}
tracepoint:sched:sched_wakeup {
    if (@start[args->pid]) {
        @sleep_us[comm] = hist((nsecs - @start[args->pid]) / 1000);
        delete(@start[args->pid]);
    }
}'

# ═══════════════════════════════════════════════════════════════════════════
# DISK I/O
# ═══════════════════════════════════════════════════════════════════════════

# Block I/O latency histogram
sudo bpftrace -e '
tracepoint:block:block_rq_issue { @start[args->dev, args->sector] = nsecs; }
tracepoint:block:block_rq_complete {
    $dur = nsecs - @start[args->dev, args->sector];
    @usecs = hist($dur / 1000);
    delete(@start[args->dev, args->sector]);
}'

# Slow disk operations (>10ms)
sudo bpftrace -e '
tracepoint:block:block_rq_issue { @start[args->dev, args->sector] = nsecs; }
tracepoint:block:block_rq_complete {
    $dur = (nsecs - @start[args->dev, args->sector]) / 1000000;
    if ($dur > 10) {
        printf("Slow I/O: %d ms, dev %d, sector %d\n", $dur, args->dev, args->sector);
    }
    delete(@start[args->dev, args->sector]);
}'

# ═══════════════════════════════════════════════════════════════════════════
# NETWORK
# ═══════════════════════════════════════════════════════════════════════════

# TCP retransmits (sign of network issues)
sudo bpftrace -e '
kprobe:tcp_retransmit_skb {
    printf("Retransmit: pid=%d comm=%s\n", pid, comm);
}'

# TCP connection latency
sudo bpftrace -e '
kprobe:tcp_v4_connect { @start[tid] = nsecs; }
kretprobe:tcp_v4_connect {
    $dur = (nsecs - @start[tid]) / 1000;
    @connect_us = hist($dur);
    delete(@start[tid]);
}'

# ═══════════════════════════════════════════════════════════════════════════
# SYSCALLS
# ═══════════════════════════════════════════════════════════════════════════

# Slow syscalls for specific process
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter /comm == "myapp"/ { @start[tid] = nsecs; }
tracepoint:raw_syscalls:sys_exit /comm == "myapp"/ {
    $dur = (nsecs - @start[tid]) / 1000;
    if ($dur > 1000) {  // > 1ms
        printf("Slow syscall: %d us, tid=%d\n", $dur, tid);
    }
    delete(@start[tid]);
}'

# Count syscalls by type
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter /comm == "myapp"/ {
    @syscalls[args->id] = count();
}'
```

### 4. Custom eBPF Program (BCC)

```python
#!/usr/bin/env python3
"""
latency_tracer.py - Trace application latency with eBPF
Requires: pip install bcc
"""

from bcc import BPF
from time import sleep, strftime
import argparse

# eBPF program
bpf_program = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

// Data structure for latency events
struct latency_event {
    u64 timestamp;
    u32 pid;
    u32 tid;
    u64 latency_ns;
    char comm[TASK_COMM_LEN];
    char func[64];
};

// Hash map to store start times
BPF_HASH(start_times, u64, u64);

// Ring buffer for events
BPF_PERF_OUTPUT(events);

// Latency histogram
BPF_HISTOGRAM(latency_hist, u64);

// Entry probe
int trace_entry(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid();
    u64 ts = bpf_ktime_get_ns();
    start_times.update(&id, &ts);
    return 0;
}

// Return probe
int trace_return(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid();
    u64 *start_ts = start_times.lookup(&id);

    if (!start_ts) {
        return 0;
    }

    u64 latency_ns = bpf_ktime_get_ns() - *start_ts;
    start_times.delete(&id);

    // Record in histogram (log2 buckets in microseconds)
    u64 latency_us = latency_ns / 1000;
    latency_hist.increment(bpf_log2l(latency_us));

    // If latency > threshold, send event
    if (latency_ns > LATENCY_THRESHOLD_NS) {
        struct latency_event event = {};
        event.timestamp = bpf_ktime_get_ns();
        event.pid = id >> 32;
        event.tid = id;
        event.latency_ns = latency_ns;
        bpf_get_current_comm(&event.comm, sizeof(event.comm));

        events.perf_submit(ctx, &event, sizeof(event));
    }

    return 0;
}

// Tracepoint for syscall latency
TRACEPOINT_PROBE(raw_syscalls, sys_enter) {
    u64 id = bpf_get_current_pid_tgid();
    u32 pid = id >> 32;

    // Filter by PID if specified
    FILTER_PID

    u64 ts = bpf_ktime_get_ns();
    start_times.update(&id, &ts);
    return 0;
}

TRACEPOINT_PROBE(raw_syscalls, sys_exit) {
    u64 id = bpf_get_current_pid_tgid();
    u32 pid = id >> 32;

    FILTER_PID

    u64 *start_ts = start_times.lookup(&id);
    if (!start_ts) {
        return 0;
    }

    u64 latency_ns = bpf_ktime_get_ns() - *start_ts;
    start_times.delete(&id);

    u64 latency_us = latency_ns / 1000;
    latency_hist.increment(bpf_log2l(latency_us));

    if (latency_ns > LATENCY_THRESHOLD_NS) {
        struct latency_event event = {};
        event.timestamp = bpf_ktime_get_ns();
        event.pid = pid;
        event.tid = id;
        event.latency_ns = latency_ns;
        bpf_get_current_comm(&event.comm, sizeof(event.comm));

        events.perf_submit(args, &event, sizeof(event));
    }

    return 0;
}
"""


def print_event(cpu, data, size):
    """Callback for latency events."""
    event = b["events"].event(data)
    print(f"{strftime('%H:%M:%S')} "
          f"PID={event.pid} TID={event.tid} "
          f"COMM={event.comm.decode('utf-8', 'replace')} "
          f"LAT={event.latency_ns / 1000000:.2f}ms")


def main():
    parser = argparse.ArgumentParser(description='Trace latency with eBPF')
    parser.add_argument('-p', '--pid', type=int, help='Filter by PID')
    parser.add_argument('-t', '--threshold', type=int, default=10,
                        help='Latency threshold in ms (default: 10)')
    parser.add_argument('-i', '--interval', type=int, default=5,
                        help='Histogram print interval in seconds')
    args = parser.parse_args()

    # Prepare BPF program
    program = bpf_program.replace(
        'LATENCY_THRESHOLD_NS',
        str(args.threshold * 1000000)  # Convert ms to ns
    )

    if args.pid:
        program = program.replace(
            'FILTER_PID',
            f'if (pid != {args.pid}) {{ return 0; }}'
        )
    else:
        program = program.replace('FILTER_PID', '')

    # Load BPF program
    global b
    b = BPF(text=program)

    # Attach to events
    b["events"].open_perf_buffer(print_event)

    print(f"Tracing latency > {args.threshold}ms... Hit Ctrl-C to end.")
    print("-" * 60)

    try:
        while True:
            # Poll for events
            b.perf_buffer_poll(timeout=1000)

            # Print histogram periodically
            sleep(args.interval)
            print(f"\n{'='*60}")
            print(f"Syscall Latency Histogram (µs):")
            b["latency_hist"].print_log2_hist("usecs")
            print(f"{'='*60}\n")

    except KeyboardInterrupt:
        print("\nFinal histogram:")
        b["latency_hist"].print_log2_hist("usecs")


if __name__ == '__main__':
    main()
```

### 5. Using BCC Tools

```bash
# ═══════════════════════════════════════════════════════════════════════════
# CPU ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

# Run queue latency histogram
sudo runqlat -m 5   # 5-second interval, milliseconds

# CPU scheduler latency
sudo cpulat 10 5    # 10 second total, 5 second intervals

# Off-CPU analysis (why process waiting)
sudo offcputime -df -p $(pgrep myapp) 30 > offcpu.svg

# ═══════════════════════════════════════════════════════════════════════════
# DISK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

# Block I/O latency histogram
sudo biolatency -m 10   # 10-second sampling

# Per-disk latency
sudo biolatency -D 10

# Trace slow I/O requests
sudo bioslower 10       # Show I/O slower than 10ms

# File system latency
sudo ext4slower 1       # ext4 operations > 1ms

# ═══════════════════════════════════════════════════════════════════════════
# NETWORK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

# TCP connection latency
sudo tcpconnlat

# TCP retransmissions
sudo tcpretrans

# Socket latency
sudo sockstat

# ═══════════════════════════════════════════════════════════════════════════
# MEMORY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

# Memory leak detection
sudo memleak -p $(pgrep myapp) 30   # Sample for 30 seconds

# Page faults
sudo hardirqs 10

# Cache misses (with perf)
sudo perf stat -e cache-misses,cache-references -p $(pgrep myapp) sleep 10

# ═══════════════════════════════════════════════════════════════════════════
# FUNCTION LATENCY
# ═══════════════════════════════════════════════════════════════════════════

# Kernel function latency
sudo funclatency do_sys_openat2

# Userspace function latency (requires debug symbols)
sudo funclatency 'c:malloc'

# Trace specific function calls
sudo trace 'do_sys_openat2 "%s", arg2'
```

### 6. Production Monitoring Script

```python
#!/usr/bin/env python3
"""
production_ebpf_monitor.py - Continuous production monitoring with eBPF
Outputs metrics in Prometheus format
"""

from bcc import BPF
from prometheus_client import start_http_server, Histogram, Counter, Gauge
import threading
import time

# Prometheus metrics
SYSCALL_LATENCY = Histogram(
    'syscall_latency_seconds',
    'Syscall latency distribution',
    ['syscall_name'],
    buckets=[.001, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)

DISK_LATENCY = Histogram(
    'disk_io_latency_seconds',
    'Disk I/O latency distribution',
    ['operation'],
    buckets=[.001, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)

RUNQUEUE_LATENCY = Histogram(
    'runqueue_latency_seconds',
    'Time process spent waiting for CPU',
    buckets=[.0001, .0005, .001, .005, .01, .025, .05, .1, .25, .5]
)

TCP_RETRANSMITS = Counter(
    'tcp_retransmits_total',
    'Number of TCP retransmissions'
)

GOROUTINE_COUNT = Gauge(
    'go_goroutines',
    'Number of goroutines (for Go applications)'
)

# eBPF programs
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

// Disk I/O latency tracking
struct disk_key {
    u64 dev;
    u64 sector;
};

BPF_HASH(disk_start, struct disk_key, u64);

TRACEPOINT_PROBE(block, block_rq_issue) {
    struct disk_key key = {.dev = args->dev, .sector = args->sector};
    u64 ts = bpf_ktime_get_ns();
    disk_start.update(&key, &ts);
    return 0;
}

TRACEPOINT_PROBE(block, block_rq_complete) {
    struct disk_key key = {.dev = args->dev, .sector = args->sector};
    u64 *ts = disk_start.lookup(&key);
    if (ts) {
        u64 latency = bpf_ktime_get_ns() - *ts;
        // Store in histogram bucket
        u64 slot = bpf_log2l(latency / 1000);  // microseconds
        @disk_latency_hist.increment(slot);
        disk_start.delete(&key);
    }
    return 0;
}

BPF_HISTOGRAM(disk_latency_hist, u64);

// Run queue latency
BPF_HASH(runq_start, u32, u64);

TRACEPOINT_PROBE(sched, sched_wakeup) {
    u64 ts = bpf_ktime_get_ns();
    u32 pid = args->pid;
    runq_start.update(&pid, &ts);
    return 0;
}

TRACEPOINT_PROBE(sched, sched_switch) {
    u32 prev = args->prev_pid;
    u32 next = args->next_pid;
    u64 ts = bpf_ktime_get_ns();

    u64 *start = runq_start.lookup(&next);
    if (start) {
        u64 delta = ts - *start;
        u64 slot = bpf_log2l(delta / 1000);
        @runq_latency_hist.increment(slot);
        runq_start.delete(&next);
    }
    return 0;
}

BPF_HISTOGRAM(runq_latency_hist, u64);

// TCP retransmit counter
BPF_ARRAY(tcp_retrans_count, u64, 1);

int trace_tcp_retransmit(struct pt_regs *ctx) {
    int key = 0;
    u64 *count = tcp_retrans_count.lookup(&key);
    if (count) {
        (*count)++;
    }
    return 0;
}
"""


class EBPFMonitor:
    def __init__(self):
        self.bpf = BPF(text=bpf_text)

        # Attach to TCP retransmit
        self.bpf.attach_kprobe(
            event="tcp_retransmit_skb",
            fn_name="trace_tcp_retransmit"
        )

        self.running = True

    def collect_metrics(self):
        """Collect metrics from eBPF maps and update Prometheus."""
        while self.running:
            # Disk latency histogram
            disk_hist = self.bpf["disk_latency_hist"]
            for k, v in disk_hist.items():
                # Convert log2 bucket to seconds
                latency_us = 2 ** k.value
                latency_sec = latency_us / 1_000_000
                DISK_LATENCY.labels(operation='all').observe(latency_sec)
            disk_hist.clear()

            # Run queue latency histogram
            runq_hist = self.bpf["runq_latency_hist"]
            for k, v in runq_hist.items():
                latency_us = 2 ** k.value
                latency_sec = latency_us / 1_000_000
                RUNQUEUE_LATENCY.observe(latency_sec)
            runq_hist.clear()

            # TCP retransmits
            retrans = self.bpf["tcp_retrans_count"][0].value
            TCP_RETRANSMITS._value.set(retrans)

            time.sleep(1)

    def stop(self):
        self.running = False


def main():
    # Start Prometheus HTTP server
    start_http_server(9090)
    print("Prometheus metrics available at :9090/metrics")

    monitor = EBPFMonitor()

    try:
        monitor.collect_metrics()
    except KeyboardInterrupt:
        monitor.stop()
        print("\nStopped monitoring")


if __name__ == '__main__':
    main()
```

### 7. Troubleshooting Flowchart

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LATENCY TROUBLESHOOTING FLOWCHART                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  START: High latency detected                                                │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────┐                                                        │
│  │ Run: runqlat    │──── High queue time? ────► CPU saturation              │
│  │ (CPU scheduling)│                           - Add more CPUs              │
│  └─────────────────┘                           - Reduce processes           │
│         │ Low                                                                │
│         ▼                                                                    │
│  ┌─────────────────┐                                                        │
│  │ Run: biolatency │──── High disk latency? ──► I/O bottleneck             │
│  │ (Disk I/O)      │                           - Faster storage             │
│  └─────────────────┘                           - Reduce I/O                 │
│         │ Low                                                                │
│         ▼                                                                    │
│  ┌─────────────────┐                                                        │
│  │Run: tcpconnlat  │──── High connect time? ──► Network issues             │
│  │    tcpretrans   │                           - Check routing              │
│  └─────────────────┘                           - Check firewalls            │
│         │ Low                                                                │
│         ▼                                                                    │
│  ┌─────────────────┐                                                        │
│  │Run: offcputime  │──── High off-CPU time? ──► Blocking calls             │
│  │ (Off-CPU)       │                           - Lock contention            │
│  └─────────────────┘                           - Synchronous I/O            │
│         │ Low                                                                │
│         ▼                                                                    │
│  ┌─────────────────┐                                                        │
│  │ Run: profile    │──── Application code? ───► Code optimization          │
│  │ (CPU profiling) │                           - Algorithm issues           │
│  └─────────────────┘                           - Memory allocation          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why This Is A Good Example

- Explains eBPF architecture clearly
- Provides ready-to-use one-liners
- Shows both bpftrace and BCC approaches
- Includes production monitoring integration
- Troubleshooting flowchart for systematic debugging

---

## Key Patterns

1. **Start Simple** - Use bpftrace one-liners first
2. **Histogram First** - See distribution, not just averages
3. **Filter by PID** - Focus on specific applications
4. **Combine Tools** - Different tools for different layers

---

**Tags:** #lowlevel #ebpf #observability #linux #performance #tracing
**Version:** 1.0.0
**Last Updated:** 2026-01-23
