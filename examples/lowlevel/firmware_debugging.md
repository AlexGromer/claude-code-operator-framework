# Example: Embedded Firmware Debugging (STM32)

## User Request

```
Отладь firmware для STM32F4 через JTAG/SWD с полным разбором crash analysis и peripheral debugging.
```

## Reasoning

**Domain:** Low-Level (Embedded systems, firmware, JTAG debugging)
**Complexity:** Complex
**Model:** Opus

## Response

### Debugging Setup: OpenOCD + GDB

```bash
# openocd.cfg - OpenOCD configuration for STM32F4
source [find interface/stlink.cfg]
source [find target/stm32f4x.cfg]

# Set SWD mode (faster than JTAG)
transport select hla_swd

# Set adapter speed (kHz)
adapter speed 2000

# Enable semihosting (printf over debug probe)
arm semihosting enable

# Flash programming settings
reset_config srst_only

# Halt on boot
init
reset halt
```

```bash
# Terminal 1: Start OpenOCD server
openocd -f openocd.cfg

# Output:
# Open On-Chip Debugger 0.12.0
# Info : Listening on port 3333 for gdb connections
# Info : stm32f4x.cpu: hardware has 6 breakpoints, 4 watchpoints
```

```bash
# Terminal 2: Connect GDB
arm-none-eabi-gdb build/firmware.elf

# GDB initialization script (.gdbinit)
target extended-remote localhost:3333
monitor reset halt
load
break main
continue
```

---

## Memory Map (STM32F4)

```
┌─────────────────────────────────────────────────────────────────────┐
│  STM32F4 Memory Layout                                               │
├─────────────────────────────────────────────────────────────────────┤
│  0x0000 0000 - 0x0007 FFFF  │  Flash alias (512 KB)                 │
│  0x0800 0000 - 0x080F FFFF  │  Flash memory (1 MB)                  │
│  0x2000 0000 - 0x2001 FFFF  │  SRAM1 (128 KB)                       │
│  0x2002 0000 - 0x2002 FFFF  │  SRAM2 (16 KB)                        │
│  0x4000 0000 - 0x5FFF FFFF  │  Peripherals                          │
│  0xE000 0000 - 0xE00F FFFF  │  Cortex-M4 internal peripherals       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## GDB Commands Reference

### Basic Operations

```gdb
# Load firmware to flash
(gdb) load

# Reset CPU
(gdb) monitor reset halt
(gdb) monitor reset run

# Continue execution
(gdb) continue
(gdb) c   # Short form

# Step through code
(gdb) step          # Step into functions
(gdb) next          # Step over functions
(gdb) stepi         # Step one instruction
(gdb) finish        # Run until function returns
```

### Breakpoints & Watchpoints

```gdb
# Set breakpoints
(gdb) break main
(gdb) break HAL_GPIO_WritePin
(gdb) break *0x08001234        # Breakpoint at address

# Conditional breakpoints
(gdb) break main if counter > 100

# Watchpoints (break on memory access)
(gdb) watch gpio_state         # Break on write
(gdb) rwatch sensor_value      # Break on read
(gdb) awatch flag              # Break on read or write

# List breakpoints
(gdb) info breakpoints

# Delete breakpoints
(gdb) delete 2                 # Delete breakpoint #2
(gdb) delete                   # Delete all
```

### Register Inspection

```gdb
# View all registers
(gdb) info registers
(gdb) info all-registers       # Include FPU registers

# Read specific registers
(gdb) print $pc                # Program counter
(gdb) print /x $sp             # Stack pointer (hex)
(gdb) print $lr                # Link register (return address)
(gdb) print $psr               # Program status register

# Cortex-M4 control registers
(gdb) print /x *(unsigned int*)0xE000ED04  # ICSR (Interrupt Control State)
(gdb) print /x *(unsigned int*)0xE000ED28  # CFSR (Fault status)
```

### Memory Inspection

```gdb
# Read memory (x = examine)
(gdb) x/4wx 0x20000000         # 4 words (hex) at SRAM start
(gdb) x/16xb 0x08000000        # 16 bytes (hex) at Flash start
(gdb) x/s 0x20001234           # String at address

# Read peripheral registers (GPIO example)
(gdb) x/4wx 0x40020000         # GPIOA base address
(gdb) x/1wx 0x40020014         # GPIOA ODR (output data register)

# Write to memory
(gdb) set *(unsigned int*)0x40020014 = 0x00000001  # Set GPIOA pin 0

# Dump memory to file
(gdb) dump binary memory flash.bin 0x08000000 0x08100000
```

### Stack Analysis

```gdb
# View stack frames
(gdb) backtrace
(gdb) bt                       # Short form
(gdb) bt full                  # Include local variables

# Example output:
# #0  HAL_Delay (Delay=1000) at stm32f4xx_hal.c:345
# #1  0x08001234 in main () at main.c:67
# #2  0x080002fe in Reset_Handler () at startup_stm32f4.s:42

# Switch stack frames
(gdb) frame 1                  # Switch to frame #1
(gdb) info locals              # View local variables in current frame
(gdb) info args                # View function arguments
```

---

## Crash Analysis: HardFault Debugging

```c
// Hard Fault Handler with debugging info
void HardFault_Handler(void) {
    __asm volatile (
        "TST LR, #4             \n"  // Test bit 2 of LR
        "ITE EQ                 \n"  // If-Then-Else
        "MRSEQ R0, MSP          \n"  // Use MSP if bit 2 == 0
        "MRSNE R0, PSP          \n"  // Use PSP if bit 2 == 1
        "B HardFault_Handler_C  \n"  // Jump to C handler
    );
}

void HardFault_Handler_C(uint32_t *hardfault_args) {
    volatile uint32_t stacked_r0;
    volatile uint32_t stacked_r1;
    volatile uint32_t stacked_r2;
    volatile uint32_t stacked_r3;
    volatile uint32_t stacked_r12;
    volatile uint32_t stacked_lr;
    volatile uint32_t stacked_pc;
    volatile uint32_t stacked_psr;

    stacked_r0  = ((uint32_t) hardfault_args[0]);
    stacked_r1  = ((uint32_t) hardfault_args[1]);
    stacked_r2  = ((uint32_t) hardfault_args[2]);
    stacked_r3  = ((uint32_t) hardfault_args[3]);
    stacked_r12 = ((uint32_t) hardfault_args[4]);
    stacked_lr  = ((uint32_t) hardfault_args[5]);
    stacked_pc  = ((uint32_t) hardfault_args[6]);
    stacked_psr = ((uint32_t) hardfault_args[7]);

    // Read fault status registers
    volatile uint32_t cfsr = (*((volatile uint32_t *)(0xE000ED28)));  // Configurable Fault Status
    volatile uint32_t hfsr = (*((volatile uint32_t *)(0xE000ED2C)));  // Hard Fault Status
    volatile uint32_t dfsr = (*((volatile uint32_t *)(0xE000ED30)));  // Debug Fault Status
    volatile uint32_t afsr = (*((volatile uint32_t *)(0xE000ED3C)));  // Auxiliary Fault Status
    volatile uint32_t bfar = (*((volatile uint32_t *)(0xE000ED38)));  // Bus Fault Address
    volatile uint32_t mmar = (*((volatile uint32_t *)(0xE000ED34)));  // MemManage Fault Address

    // Set breakpoint here in GDB to inspect values
    __asm("BKPT #0");

    while (1);  // Halt
}
```

### Fault Register Decoding (GDB)

```gdb
# When stopped in HardFault_Handler_C

# Print stacked context
(gdb) print /x stacked_pc      # Faulting instruction address
(gdb) print /x stacked_lr      # Return address
(gdb) print /x stacked_psr     # Processor status

# Decode CFSR (Configurable Fault Status Register)
(gdb) print /t cfsr            # Binary format

# CFSR bits:
# - IACCVIOL (bit 0): Instruction access violation
# - DACCVIOL (bit 1): Data access violation
# - MUNSTKERR (bit 3): MemManage fault on unstacking
# - MSTKERR (bit 4): MemManage fault on stacking
# - IMPRECISERR (bit 10): Imprecise data bus error
# - PRECISERR (bit 9): Precise data bus error
# - IBUSERR (bit 8): Instruction bus error

# Example: CFSR = 0x00000200 (bit 9 set)
# → Precise data bus error at address in BFAR

(gdb) print /x bfar            # Bus Fault Address (where fault occurred)

# Disassemble around faulting address
(gdb) disassemble stacked_pc
```

---

## Peripheral Debugging (GPIO Example)

```c
// Buggy code: GPIO not initialized properly
void gpio_bug_demo(void) {
    // BUG: Forgot to enable clock
    // __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_5;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    // This will fail silently (or hard fault on some chips)
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
}
```

### Debugging via GDB

```gdb
# Break in HAL_GPIO_Init
(gdb) break HAL_GPIO_Init
(gdb) continue

# Check if clock is enabled (RCC register)
(gdb) x/1wx 0x40023830         # RCC_AHB1ENR (AHB1 peripheral clock enable)
# Expected: bit 0 set (GPIOAEN = 1)
# Actual: 0x00000000 → Clock not enabled!

# Manually enable clock (workaround for testing)
(gdb) set *(unsigned int*)0x40023830 = 0x00000001

# Continue and verify GPIO works now
(gdb) continue

# Inspect GPIO registers after write
(gdb) x/4wx 0x40020000         # GPIOA base
# +0x00: MODER   (mode register)
# +0x04: OTYPER  (output type)
# +0x08: OSPEEDR (output speed)
# +0x0C: PUPDR   (pull-up/pull-down)
# +0x14: ODR     (output data)

(gdb) x/1wx 0x40020014         # GPIOA ODR
# Expected: 0x00000020 (pin 5 set)
```

---

## Real-Time Trace (SWO/ITM)

```c
// Enable ITM for printf over SWO
#include <stdio.h>

int _write(int file, char *ptr, int len) {
    for (int i = 0; i < len; i++) {
        ITM_SendChar((*ptr++));
    }
    return len;
}

void main(void) {
    // ITM already enabled by debugger

    printf("Firmware booted\n");
    printf("CPU freq: %lu Hz\n", SystemCoreClock);

    while (1) {
        printf("Sensor: %d\n", read_sensor());
        HAL_Delay(100);
    }
}
```

```bash
# OpenOCD: Enable SWO trace
(gdb) monitor tpiu config internal swotrace.log uart off 168000000
(gdb) monitor itm port 0 on

# View trace in real-time
tail -f swotrace.log
```

---

## RTOS Debugging (FreeRTOS)

```gdb
# List all tasks
(gdb) info threads

# Example output:
# * 1    Thread 536873504 (task1) 0x08001234 in vTaskDelay ()
#   2    Thread 536874000 (task2) 0x08002468 in xQueueReceive ()
#   3    Thread 536874496 (IDLE) 0x08003000 in prvIdleTask ()

# Switch to task 2
(gdb) thread 2

# View task stack
(gdb) backtrace

# Print FreeRTOS task list
(gdb) call vTaskList((char*)0x20001000)
(gdb) x/200s 0x20001000

# Example output:
# Name          State  Priority  Stack  Num
# ------------------------------------------
# task1         Ready  1         256    1
# task2         Blocked 2        512    2
# IDLE          Ready  0         128    3
```

---

## Common Embedded Bugs & How to Debug

### 1. Stack Overflow

```gdb
# Symptoms: Random crashes, corruption of local variables

# Check stack usage
(gdb) info stack
(gdb) print $sp
(gdb) print __StackLimit       # Linker symbol

# If $sp < __StackLimit → Stack overflow!

# Solution: Increase stack size in linker script
_Min_Stack_Size = 0x1000;  # 4 KB (was 0x400 / 1 KB)
```

### 2. Uninitialized Pointer Dereference

```c
// Buggy code
uint32_t *ptr;  // Uninitialized
*ptr = 0x1234;  // Hard Fault (access violation)
```

```gdb
# GDB catches fault
(gdb) print /x ptr
# Output: 0xcccccccc (garbage)

# Decode fault
(gdb) print /x cfsr
# Output: 0x00000001 (IACCVIOL: instruction access violation)
```

### 3. Race Condition (Missing Critical Section)

```c
// Buggy code (interrupt and main access same variable)
volatile uint32_t counter = 0;

void TIM2_IRQHandler(void) {
    counter++;  // Race condition!
}

void main(void) {
    counter += 10;  // Not atomic!
}
```

```gdb
# Debug with watchpoint
(gdb) watch counter

# GDB breaks on every write → observe interleaving
```

---

## Flash/Bootloader Debugging

```gdb
# Verify flash contents match ELF
(gdb) compare-sections

# Example output:
# Section .text, range 0x8000000 -- 0x8001234: matched.
# Section .rodata, range 0x8001234 -- 0x8002000: MIS-MATCHED!

# Dump flash to file
(gdb) dump binary memory flash_dump.bin 0x08000000 0x08100000

# Compare with original
$ hexdump -C flash_dump.bin | head
$ hexdump -C firmware.bin | head

# Erase flash
(gdb) monitor flash erase_sector 0 0 11  # Erase sectors 0-11

# Re-flash
(gdb) load
```

---

## Key Takeaways

1. **OpenOCD + GDB** — Industry standard for ARM debugging
2. **Fault analysis** — Decode CFSR/HFSR to find crash cause
3. **Peripheral debugging** — Read/write registers directly via GDB
4. **SWO trace** — Real-time printf without UART (non-intrusive)
5. **RTOS-aware debugging** — Inspect tasks, stacks, queues
6. **Watchpoints** — Find race conditions and memory corruption

**Tools:** OpenOCD, GDB, ST-Link, J-Link, Segger Ozone
**Speed:** Flash once, debug infinitely (no reflash needed)
**Best practice:** Add fault handlers with register dumps
