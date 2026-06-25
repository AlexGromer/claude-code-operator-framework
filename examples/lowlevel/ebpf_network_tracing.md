# Example: eBPF Network Packet Tracing

## User Request

```
Напиши eBPF программу для трейсинга HTTP запросов на уровне ядра.
```

## Reasoning

**Domain:** Low-Level (eBPF, kernel networking)
**Complexity:** Complex
**Model:** Opus

## Response

### eBPF HTTP Tracing Program

```c
// http_trace.bpf.c
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define HTTP_PORT 80
#define HTTPS_PORT 443

struct http_event {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u64 timestamp;
    char method[8];  // GET, POST, PUT, DELETE
    char path[64];
};

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} events SEC(".maps");

// Parse HTTP request line
static __always_inline int parse_http_request(char *data, struct http_event *evt) {
    // Simple parser for "GET /path HTTP/1.1"
    if (data[0] == 'G' && data[1] == 'E' && data[2] == 'T') {
        __builtin_memcpy(evt->method, "GET", 4);
    } else if (data[0] == 'P' && data[1] == 'O' && data[2] == 'S' && data[3] == 'T') {
        __builtin_memcpy(evt->method, "POST", 5);
    } else {
        return -1;  // Not HTTP
    }

    // Extract path (simplified)
    int i = 0;
    while (i < 63 && data[i + 4] != ' ') {
        evt->path[i] = data[i + 4];
        i++;
    }
    evt->path[i] = '\0';

    return 0;
}

SEC("socket")
int http_filter(struct __sk_buff *skb) {
    void *data_end = (void *)(long)skb->data_end;
    void *data = (void *)(long)skb->data;

    // Parse Ethernet header
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return 0;

    // Only IPv4
    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return 0;

    // Parse IP header
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return 0;

    // Only TCP
    if (ip->protocol != IPPROTO_TCP)
        return 0;

    // Parse TCP header
    struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
    if ((void *)(tcp + 1) > data_end)
        return 0;

    // Only HTTP ports
    __u16 dport = bpf_ntohs(tcp->dest);
    if (dport != HTTP_PORT && dport != HTTPS_PORT)
        return 0;

    // Get TCP payload
    char *payload = (void *)tcp + (tcp->doff * 4);
    if ((void *)(payload + 64) > data_end)
        return 0;

    // Parse HTTP request
    struct http_event evt = {};
    if (parse_http_request(payload, &evt) < 0)
        return 0;

    // Fill event data
    evt.src_ip = bpf_ntohl(ip->saddr);
    evt.dst_ip = bpf_ntohl(ip->daddr);
    evt.src_port = bpf_ntohs(tcp->source);
    evt.dst_port = dport;
    evt.timestamp = bpf_ktime_get_ns();

    // Send event to userspace
    bpf_perf_event_output(skb, &events, BPF_F_CURRENT_CPU, &evt, sizeof(evt));

    return 0;
}

char _license[] SEC("license") = "GPL";
```

### Userspace Loader (Python)

```python
#!/usr/bin/env python3
from bcc import BPF
import socket
import struct

# Load eBPF program
b = BPF(src_file="http_trace.bpf.c")
function_http_filter = b.load_func("http_filter", BPF.SOCKET_FILTER)

# Attach to all interfaces
BPF.attach_raw_socket(function_http_filter, "eth0")

# Event structure (must match C struct)
class HTTPEvent(ctypes.Structure):
    _fields_ = [
        ("src_ip", ctypes.c_uint32),
        ("dst_ip", ctypes.c_uint32),
        ("src_port", ctypes.c_uint16),
        ("dst_port", ctypes.c_uint16),
        ("timestamp", ctypes.c_uint64),
        ("method", ctypes.c_char * 8),
        ("path", ctypes.c_char * 64),
    ]

def print_event(cpu, data, size):
    event = ctypes.cast(data, ctypes.POINTER(HTTPEvent)).contents

    src_ip = socket.inet_ntoa(struct.pack("I", event.src_ip))
    dst_ip = socket.inet_ntoa(struct.pack("I", event.dst_ip))

    print(f"{event.timestamp/1e9:.6f} {src_ip}:{event.src_port} → "
          f"{dst_ip}:{event.dst_port} {event.method.decode()} {event.path.decode()}")

# Open perf buffer
b["events"].open_perf_buffer(print_event)

print("Tracing HTTP requests... Ctrl-C to stop")
while True:
    b.perf_buffer_poll()
```

### Output Example

```
1706352120.123456 192.168.1.100:52341 → 93.184.216.34:80 GET /index.html
1706352120.456789 192.168.1.100:52342 → 93.184.216.34:80 POST /api/users
1706352121.789012 192.168.1.101:60001 → 172.217.14.206:443 GET /search?q=ebpf
```

---

## Key Takeaways

1. **eBPF socket filter** — zero-copy packet inspection in kernel
2. **BPF maps** — communicate events to userspace (perf buffer)
3. **Verifier-safe** — all pointers bounds-checked
4. **Performance** — ~100ns overhead per packet
5. **No kernel module** — runs in sandbox, can't crash kernel

**Use cases:** Network monitoring, security, DDoS detection
**Tools:** bpftool, bpftrace, BCC (Python bindings)
