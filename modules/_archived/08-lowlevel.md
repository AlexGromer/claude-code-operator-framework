# Module 08: Low-Level Development

## Purpose

Systems programming, kernel development, embedded systems,
reverse engineering, and low-level languages (Go, C, Rust, Assembly).

---

## Section 1: Language Reference

### 1.1 Go

```go
// Go - Primary for CLI tools, network services, security tools

// Project structure
project/
├── cmd/
│   ─── app/
│       ─── main.go
├── internal/
│   ├── config/
│   ─── handler/
├── pkg/
│   ─── util/
├── go.mod
─── go.sum

// Common patterns
// Error handling
func doSomething() error {
    result, err := operation()
    if err != nil {
        return fmt.Errorf("operation failed: %w", err)
    }
    return nil
}

// Concurrency
func worker(jobs <-chan Job, results chan<- Result) {
    for job := range jobs {
        results <- process(job)
    }
}

// Context for cancellation
func longOperation(ctx context.Context) error {
    select {
    case <-ctx.Done():
        return ctx.Err()
    case result := <-doWork():
        return nil
    }
}
```

**Go Tools:**
```bash
go build -ldflags="-s -w" -o app    # Optimized build
go test -race ./...                  # Race detector
go vet ./...                         # Static analysis
golangci-lint run                    # Comprehensive lint
go mod tidy                          # Clean dependencies
```

### 1.2 C

```c
// C - For kernel modules, embedded, performance-critical code

// Memory management patterns
#include <stdlib.h>
#include <string.h>

// Safe allocation with zeroing
void *safe_alloc(size_t size) {
    void *ptr = calloc(1, size);
    if (!ptr) {
        perror("allocation failed");
        exit(EXIT_FAILURE);
    }
    return ptr;
}

// RAII-style cleanup (GCC/Clang)
#define CLEANUP(func) __attribute__((cleanup(func)))

void free_ptr(void *p) {
    free(*(void **)p);
}

void example() {
    CLEANUP(free_ptr) char *buf = malloc(1024);
    // buf automatically freed when scope exits
}

// Buffer overflow prevention
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

void safe_copy(char *dst, size_t dst_size, const char *src) {
    strncpy(dst, src, dst_size - 1);
    dst[dst_size - 1] = '\0';
}
```

**C Tools:**
```bash
gcc -Wall -Wextra -Werror -O2 -o app main.c  # Strict compilation
clang --analyze main.c                         # Static analysis
valgrind --leak-check=full ./app               # Memory checking
gdb ./app                                      # Debugging
```

### 1.3 Rust

```rust
// Rust - Memory-safe systems programming

// Project structure
project/
├── Cargo.toml
├── src/
│   ├── main.rs
│   ├── lib.rs
│   ─── module/
│       ─── mod.rs
─── tests/
    ─── integration_test.rs

// Error handling with Result
use std::error::Error;

fn read_config(path: &str) -> Result<Config, Box<dyn Error>> {
    let content = std::fs::read_to_string(path)?;
    let config: Config = serde_json::from_str(&content)?;
    Ok(config)
}

// Safe concurrency with channels
use std::sync::mpsc;
use std::thread;

fn parallel_work() {
    let (tx, rx) = mpsc::channel();
    
    thread::spawn(move || {
        tx.send(compute()).unwrap();
    });
    
    let result = rx.recv().unwrap();
}
```

**Rust Tools:**
```bash
cargo build --release              # Optimized build
cargo test                         # Run tests
cargo clippy                       # Linting
cargo fmt                          # Formatting
cargo audit                        # Security audit
```

### 1.4 Assembly (x86-64)

```nasm
; Basic structure (NASM syntax)
section .data
    msg db "Hello", 0xa, 0      ; String with newline
    len equ $ - msg

section .bss
    buffer resb 256             ; Reserve 256 bytes

section .text
    global _start

_start:
    ; syscall: write(1, msg, len)
    mov rax, 1                  ; syscall number (write)
    mov rdi, 1                  ; fd (stdout)
    mov rsi, msg                ; buffer
    mov rdx, len                ; count
    syscall

    ; syscall: exit(0)
    mov rax, 60                 ; syscall number (exit)
    xor rdi, rdi                ; status = 0
    syscall

; Common calling convention (System V AMD64)
; Arguments: rdi, rsi, rdx, rcx, r8, r9, then stack
; Return: rax
; Caller-saved: rax, rcx, rdx, rsi, rdi, r8, r9, r10, r11
; Callee-saved: rbx, rbp, r12, r13, r14, r15
```

**Assembly Tools:**
```bash
nasm -f elf64 -o prog.o prog.asm   # Assemble
ld -o prog prog.o                   # Link
objdump -d prog                     # Disassemble
```

### 1.5 Groovy (Jenkins Pipelines)

```groovy
// Groovy - For Jenkins pipelines

// Pipeline example
pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = "app:${BUILD_NUMBER}"
    }
    
    stages {
        stage('Build') {
            steps {
                script {
                    sh 'docker build -t ${DOCKER_IMAGE} .'
                }
            }
        }
        
        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps { sh 'make test-unit' }
                }
                stage('Integration Tests') {
                    steps { sh 'make test-integration' }
                }
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            input {
                message "Deploy to production?"
            }
            steps {
                sh 'kubectl apply -f k8s/'
            }
        }
    }
    
    post {
        always { cleanWs() }
        failure { slackSend color: 'danger', message: "Failed" }
    }
}
```

---

## Section 2: eBPF Development

### 2.1 eBPF Overview

```
┌─────────────────────────────────────────────────────────────────────────────└
│                           eBPF Architecture                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Space                                                                  │
│  ┌─────────────└    ┌─────────────└                                        │
│  │ bpftrace    │    │ BCC/libbpf  │                                        │
│  ───────┬──────┘    ───────┬──────┘                                        │
│         │                   │                                                │
│  ───────┼───────────────────┼─────────── System Call Interface ─────────── │
│         │                   │                                                │
│  Kernel │                   │                                                │
│  ┌──────▼───────────────────▼──────└                                        │
│  │         eBPF Verifier           │  (Safety checks)                       │
│  ───────────────┬──────────────────┘                                        │
│                 │                                                            │
│  ┌──────────────▼──────────────────└                                        │
│  │         JIT Compiler            │  (Native code)                         │
│  ───────────────┬──────────────────┘                                        │
│                 │                                                            │
│  ┌──────────────▼──────────────────└                                        │
│  │      Attachment Points          │                                        │
│  │  • kprobes  • tracepoints       │                                        │
│  │  • XDP      • TC                │                                        │
│  │  • LSM      • uprobes           │                                        │
│  ──────────────────────────────────┘                                        │
──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 eBPF Program Types

| Type | Attachment | Use Case |
|------|------------|----------|
| **kprobe/kretprobe** | Kernel functions | Tracing, debugging |
| **tracepoint** | Static trace points | Performance analysis |
| **XDP** | Network driver | Fast packet processing |
| **TC** | Traffic control | Network filtering |
| **LSM** | Security hooks | Security policies |
| **uprobe/uretprobe** | User-space functions | Application tracing |
| **perf_event** | Performance counters | Profiling |

### 2.3 bpftrace Examples

```bash
# List available probes
bpftrace -l 'tracepoint:*'

# Count syscalls by process
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# Trace file opens
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Histogram of read sizes
bpftrace -e 'tracepoint:syscalls:sys_exit_read /args->ret > 0/ { @bytes = hist(args->ret); }'

# Function latency
bpftrace -e 'kprobe:vfs_read { @start[tid] = nsecs; }
             kretprobe:vfs_read /@start[tid]/ { 
               @ns = hist(nsecs - @start[tid]); 
               delete(@start[tid]); 
             }'
```

### 2.4 libbpf-based Program

```c
// Minimal eBPF program (libbpf)
// bpf_prog.bpf.c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("tracepoint/syscalls/sys_enter_execve")
int trace_execve(struct trace_event_raw_sys_enter *ctx)
{
    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));
    bpf_printk("execve by %s\n", comm);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

---

## Section 3: Kernel Development

### 3.1 Kernel Module Skeleton

```c
// hello.c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Author Name");
MODULE_DESCRIPTION("Example kernel module");
MODULE_VERSION("1.0");

static int param_value = 0;
module_param(param_value, int, S_IRUGO);
MODULE_PARM_DESC(param_value, "An integer parameter");

static int __init hello_init(void)
{
    printk(KERN_INFO "Hello, kernel! param=%d\n", param_value);
    return 0;  // 0 = success, negative = error
}

static void __exit hello_exit(void)
{
    printk(KERN_INFO "Goodbye, kernel!\n");
}

module_init(hello_init);
module_exit(hello_exit);
```

```makefile
# Makefile
obj-m += hello.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean

install:
	sudo insmod hello.ko param_value=42

remove:
	sudo rmmod hello
```

### 3.2 Kernel Debugging

```bash
# View kernel messages
dmesg -w                           # Watch live
dmesg | tail -50                   # Last 50 lines
journalctl -k                      # Kernel log via systemd

# Module info
lsmod                              # List loaded modules
modinfo hello                      # Module information
cat /proc/modules                  # Module details

# Kernel symbols
cat /proc/kallsyms | grep function_name
```

---

## Section 4: Embedded Development

### 4.1 STM32 Development

```c
// STM32 bare-metal example (CMSIS)
#include "stm32f4xx.h"

void SystemInit(void) {
    // Clock configuration
    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY));
}

void GPIO_Init(void) {
    // Enable GPIOA clock
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    
    // Configure PA5 as output (LED)
    GPIOA->MODER |= GPIO_MODER_MODER5_0;
}

void delay(uint32_t ms) {
    for (volatile uint32_t i = 0; i < ms * 4000; i++);
}

int main(void) {
    GPIO_Init();
    
    while (1) {
        GPIOA->ODR ^= GPIO_ODR_OD5;  // Toggle LED
        delay(500);
    }
}
```

### 4.2 ESP32 Development (Arduino Framework)

```cpp
// ESP32 with WiFi and MQTT
#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "SSID";
const char* password = "PASSWORD";
const char* mqtt_server = "broker.example.com";

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
    Serial.begin(115200);
    
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }
    
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);
}

void callback(char* topic, byte* payload, unsigned int length) {
    // Handle incoming messages
}

void reconnect() {
    while (!client.connected()) {
        if (client.connect("ESP32Client")) {
            client.subscribe("home/sensor/#");
        } else {
            delay(5000);
        }
    }
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();
    
    // Publish sensor data
    float temp = readTemperature();
    client.publish("home/sensor/temp", String(temp).c_str());
    delay(60000);
}
```

---

## Section 5: Reverse Engineering

### 5.1 Analysis Workflow

```
┌─────────────────────────────────────────────────────────────────────────────└
│                    Reverse Engineering Workflow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. INFORMATION GATHERING                                                    │
│     ──► file, strings, readelf, objdump                                     │
│                                                                              │
│  2. STATIC ANALYSIS                                                          │
│     ──► Disassembly (Ghidra, IDA, r2)                                       │
│     ──► Decompilation                                                        │
│     ──► Control flow analysis                                                │
│                                                                              │
│  3. DYNAMIC ANALYSIS                                                         │
│     ──► Debugging (gdb, x64dbg)                                             │
│     ──► Tracing (strace, ltrace)                                            │
│     ──► Instrumentation                                                      │
│                                                                              │
│  4. BEHAVIORAL ANALYSIS                                                      │
│     ──► Sandbox execution                                                    │
│     ──► Network monitoring                                                   │
│     ──► File system monitoring                                               │
──────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 RE Tools Reference

| Tool | Purpose | Command |
|------|---------|---------|
| **file** | File type identification | `file binary` |
| **strings** | Extract strings | `strings -a binary` |
| **readelf** | ELF structure | `readelf -a binary` |
| **objdump** | Disassembly | `objdump -d binary` |
| **nm** | Symbol table | `nm binary` |
| **ldd** | Dependencies | `ldd binary` |
| **strace** | System call tracing | `strace ./binary` |
| **ltrace** | Library call tracing | `ltrace ./binary` |
| **radare2** | RE framework | `r2 -A binary` |
| **Ghidra** | Decompiler | GUI tool |
| **gdb** | Debugger | `gdb ./binary` |

### 5.3 GDB Quick Reference

```bash
# Basic commands
gdb ./binary                       # Start
run [args]                         # Run program
break main                         # Set breakpoint
break *0x401234                    # Break at address
continue                           # Continue execution
stepi                              # Step instruction
nexti                              # Next instruction (skip calls)
info registers                     # Show registers
x/10i $rip                         # Examine 10 instructions at RIP
x/20wx $rsp                        # Examine 20 words at RSP
disassemble main                   # Disassemble function
set $rax = 0                       # Modify register
```

### 5.4 radare2 Quick Reference

```bash
r2 binary                          # Open
aaa                                # Analyze all
afl                                # List functions
s main                             # Seek to main
pdf                                # Print disassembly
VV                                 # Visual graph mode
px 100                             # Print 100 hex bytes
iz                                 # List strings
ii                                 # List imports
iE                                 # List exports
```

---

## Section 6: Quick Commands Reference

```bash
# === Go ===
go build -ldflags="-s -w" -o app cmd/app/main.go
go test -v -race -cover ./...
golangci-lint run

# === C ===
gcc -Wall -Wextra -O2 -o app main.c
valgrind --leak-check=full ./app
gdb -tui ./app

# === Rust ===
cargo build --release
cargo test
cargo clippy -- -D warnings

# === Assembly ===
nasm -f elf64 prog.asm -o prog.o
ld -o prog prog.o

# === Kernel Module ===
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
sudo insmod module.ko
sudo rmmod module

# === eBPF ===
bpftrace -e 'tracepoint:syscalls:sys_enter_* { @[probe] = count(); }'
sudo bpftool prog list

# === Reverse Engineering ===
file binary && strings -a binary
r2 -A binary -c "aaa; afl; q"
strace -f ./binary 2>&1 | tee strace.log
```

---

## Few-Shot Examples

### Systems Programming
| Задача | Пример | Описание |
|--------|--------|----------|
| Kernel Module | `~/.claude/examples/lowlevel/kernel_module_development.md` | Разработка модуля ядра |
| Custom Allocator | `~/.claude/examples/lowlevel/custom_allocator.md` | Кастомный аллокатор |
| Assembly Opt | `~/.claude/examples/lowlevel/assembly_optimization.md` | Оптимизация на ассемблере |

### eBPF
| Задача | Пример | Описание |
|--------|--------|----------|
| eBPF Observability | `~/.claude/examples/lowlevel/ebpf_observability.md` | Мониторинг через eBPF |
| Network Tracing | `~/.claude/examples/lowlevel/ebpf_network_tracing.md` | Трассировка сети |

### Language-Specific
| Задача | Пример | Описание |
|--------|--------|----------|
| Go Optimization | `~/.claude/examples/lowlevel/go_optimization.md` | Оптимизация Go |
| Rust Memory | `~/.claude/examples/lowlevel/rust_memory_safety.md` | Memory safety в Rust |
| Firmware Debug | `~/.claude/examples/lowlevel/firmware_debugging.md` | Отладка прошивок |

**Использование:** Прочитай пример перед низкоуровневой задачей для понимания глубины анализа.

---

## Уточняющие вопросы (Clarification Questions)

Когда пользователь задаёт задачу в этом домене без достаточных деталей, задайте следующие вопросы:

### Общие вопросы

| Вопрос | Когда задавать | Критичность |
|--------|---------------|-------------|
| Какая целевая архитектура? (x86-64, ARM, RISC-V, Xtensa) | Низкоуровневая разработка, ассемблер, embedded | 🔴 |
| Какая целевая ОС? (Linux, bare-metal, RTOS, Windows) | Kernel modules, драйверы | 🔴 |
| Какая версия ядра? (если Linux kernel development) | Kernel modules, eBPF | 🔴 |
| Какие инструменты debug доступны? (gdb, JTAG, serial, QEMU) | Embedded, отладка | 🟡 |
| Есть доступ к hardware? (физическое устройство, эмулятор, симулятор) | Embedded, IoT, firmware | 🔴 |
| Какие ограничения по размеру? (ROM, RAM, Flash) | Embedded, firmware optimization | 🟡 |
| Какие safety constraints? (нельзя reboot, production env, timing critical) | Kernel, embedded, critical systems | 🔴 |
| Требования по real-time? (hard/soft real-time, latency limits) | Embedded, RTOS, kernel | 🟡 |
| Есть SDK/toolchain? (vendor-specific tools, cross-compiler) | Embedded, microcontroller | 🟡 |

### Специфические вопросы по типам задач

**Kernel Module Development:**
- Какая версия kernel headers установлена?
- Статический или динамический модуль?
- Требуется ли поддержка нескольких версий ядра?
- Есть ли зависимости от других модулей?
- Module parameters нужны?

**eBPF Development:**
- Для чего нужен eBPF? (observability, networking, security, profiling)
- Attachment point? (kprobe, tracepoint, XDP, TC, LSM)
- Target kernel version? (BPF features зависят от версии)
- Использовать bpftrace (simple) или libbpf (production)?
- CO-RE (Compile Once, Run Everywhere) нужен?

**Embedded/IoT:**
- Какой микроконтроллер? (STM32, ESP32, nRF52, RP2040, Arduino)
- Framework? (Arduino, ESP-IDF, STM32 HAL, bare-metal)
- Коммуникация? (UART, SPI, I2C, WiFi, BLE, LoRa)
- Питание? (battery, USB, external PSU — влияет на power management)
- Прошивка через? (USB, JTAG, OTA, serial bootloader)

**Reverse Engineering:**
- Какой формат? (ELF, PE, raw binary, firmware image)
- Какая архитектура? (x86-64, ARM, MIPS, другое)
- Цель? (vulnerability research, malware analysis, protocol reverse, crack)
- Статический или динамический анализ?
- Есть symbols или stripped?
- Есть anti-RE techniques? (obfuscation, packing, anti-debug)

**Performance Optimization:**
- Какой язык? (C, Rust, Go, Assembly)
- Bottleneck уже идентифицирован? (profiling сделан?)
- Target metric? (latency, throughput, memory, energy)
- Constraints? (нельзя менять API, backward compatibility)

**Memory Management:**
- Custom allocator нужен? (pool, slab, arena)
- Target? (kernel space, user space, embedded)
- Alignment requirements?
- Thread-safety нужна?

---

## Уровни авторизации (Authorization Levels)

| Операция | Уровень | Подтверждение |
|----------|---------|---------------|
| Чтение исходников | READ | Нет |
| Анализ бинарников (static) | ANALYZE | Нет |
| Компиляция кода (без установки) | ANALYZE | Нет |
| Написание кода (не kernel) | MODIFY | Да |
| Написание kernel module | MODIFY | Да + review |
| Загрузка kernel module (insmod) | INFRASTRUCTURE | Да + warning |
| Выгрузка kernel module (rmmod) | INFRASTRUCTURE | Да |
| eBPF attach (observability) | NETWORK_ACTIVE | Да (scope: read-only) |
| eBPF attach (packet drop, modify) | NETWORK_ACTIVE | Да + scope |
| Firmware flashing (embedded) | DESTRUCTIVE | Да + backup check |
| Memory write (debug) | CREDENTIAL | Да + scope (address range) |
| Kernel patch (production) | DESTRUCTIVE | Да + explicit |
| Reboot system | DESTRUCTIVE | Да + explicit |
| Hardware access (GPIO, registers) | INFRASTRUCTURE | Да |
| Disassembly (own binaries) | ANALYZE | Нет |
| Disassembly (third-party) | ANALYZE | Да (legal check) |
| Exploit development (research) | CREDENTIAL | Да + scope + disclosure |
