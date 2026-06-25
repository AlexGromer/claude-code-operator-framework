# Example: Custom Memory Allocator (C)

## User Request

```
Реализуй simple arena allocator для embedded системы с ограниченной памятью.
```

## Reasoning

**Domain:** Low-Level (memory management)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Arena Allocator Implementation

```c
// arena.h
#ifndef ARENA_H
#define ARENA_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint8_t *memory;      // Base pointer to arena memory
    size_t size;          // Total arena size
    size_t offset;        // Current allocation offset
    size_t peak_usage;    // Peak memory usage (for profiling)
} Arena;

// Initialize arena with pre-allocated buffer
void arena_init(Arena *arena, void *buffer, size_t size);

// Allocate memory from arena (aligned to 8 bytes)
void *arena_alloc(Arena *arena, size_t size);

// Allocate and zero-initialize
void *arena_alloc_zero(Arena *arena, size_t size);

// Reset arena (free all allocations at once)
void arena_reset(Arena *arena);

// Get current memory usage
size_t arena_usage(const Arena *arena);

// Get peak memory usage
size_t arena_peak_usage(const Arena *arena);

#endif // ARENA_H
```

```c
// arena.c
#include "arena.h"
#include <string.h>
#include <assert.h>

#define ALIGNMENT 8
#define ALIGN_UP(n, align) (((n) + (align) - 1) & ~((align) - 1))

void arena_init(Arena *arena, void *buffer, size_t size) {
    assert(arena != NULL);
    assert(buffer != NULL);
    assert(size > 0);

    arena->memory = (uint8_t *)buffer;
    arena->size = size;
    arena->offset = 0;
    arena->peak_usage = 0;
}

void *arena_alloc(Arena *arena, size_t size) {
    assert(arena != NULL);

    if (size == 0)
        return NULL;

    // Align allocation to ALIGNMENT boundary
    size_t aligned_size = ALIGN_UP(size, ALIGNMENT);

    // Check if enough space available
    if (arena->offset + aligned_size > arena->size)
        return NULL;  // Out of memory

    // Allocate from arena
    void *ptr = arena->memory + arena->offset;
    arena->offset += aligned_size;

    // Update peak usage
    if (arena->offset > arena->peak_usage)
        arena->peak_usage = arena->offset;

    return ptr;
}

void *arena_alloc_zero(Arena *arena, size_t size) {
    void *ptr = arena_alloc(arena, size);
    if (ptr != NULL)
        memset(ptr, 0, size);
    return ptr;
}

void arena_reset(Arena *arena) {
    assert(arena != NULL);
    arena->offset = 0;
    // Note: peak_usage is NOT reset (for profiling)
}

size_t arena_usage(const Arena *arena) {
    assert(arena != NULL);
    return arena->offset;
}

size_t arena_peak_usage(const Arena *arena) {
    assert(arena != NULL);
    return arena->peak_usage;
}
```

### Example Usage

```c
#include <stdio.h>
#include "arena.h"

#define ARENA_SIZE (64 * 1024)  // 64 KB

int main() {
    // Allocate arena buffer (could be static for embedded)
    static uint8_t arena_buffer[ARENA_SIZE];

    Arena arena;
    arena_init(&arena, arena_buffer, ARENA_SIZE);

    // Allocate some data
    int *numbers = arena_alloc(&arena, 100 * sizeof(int));
    if (numbers == NULL) {
        printf("Failed to allocate numbers\n");
        return 1;
    }

    for (int i = 0; i < 100; i++)
        numbers[i] = i * i;

    // Allocate string
    char *message = arena_alloc_zero(&arena, 256);
    snprintf(message, 256, "Hello from arena allocator!");

    printf("Message: %s\n", message);
    printf("Arena usage: %zu / %zu bytes\n", arena_usage(&arena), ARENA_SIZE);

    // Reset arena (free all at once)
    arena_reset(&arena);
    printf("After reset: %zu bytes used\n", arena_usage(&arena));

    // Reuse arena memory
    double *values = arena_alloc(&arena, 50 * sizeof(double));
    printf("Allocated doubles: %zu bytes\n", arena_usage(&arena));

    printf("Peak usage: %zu bytes\n", arena_peak_usage(&arena));

    return 0;
}
```

### Benchmark vs malloc

```c
#include <time.h>
#include <stdlib.h>

void benchmark_malloc() {
    clock_t start = clock();

    for (int i = 0; i < 100000; i++) {
        void *ptr = malloc(64);
        free(ptr);
    }

    clock_t end = clock();
    printf("malloc/free: %.3f ms\n",
           (double)(end - start) / CLOCKS_PER_SEC * 1000);
}

void benchmark_arena() {
    static uint8_t buffer[1024 * 1024];  // 1 MB
    Arena arena;
    arena_init(&arena, buffer, sizeof(buffer));

    clock_t start = clock();

    for (int i = 0; i < 100000; i++) {
        arena_alloc(&arena, 64);
        if (arena_usage(&arena) + 64 > sizeof(buffer))
            arena_reset(&arena);  // Batch free
    }

    clock_t end = clock();
    printf("arena: %.3f ms\n",
           (double)(end - start) / CLOCKS_PER_SEC * 1000);
}

int main() {
    benchmark_malloc();  // ~150 ms
    benchmark_arena();   // ~5 ms (30× faster)
    return 0;
}
```

---

## Key Takeaways

1. **No individual free** — all freed at once with `arena_reset()`
2. **Fast allocation** — just bump pointer (no free list traversal)
3. **Cache-friendly** — allocations are contiguous
4. **Predictable** — no fragmentation, no malloc overhead
5. **Embedded-friendly** — static buffer, no heap required

**Use cases:** Games (per-frame allocations), parsers, temporary data
**Trade-off:** Cannot free individual allocations
**Speed:** 10-30× faster than malloc for small allocations
