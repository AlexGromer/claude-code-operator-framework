# Example: Linux Kernel Module Development

## User Request

```
Напиши простой kernel module для логирования syscall'ов.
```

## Reasoning

**Domain:** Low-Level (kernel module)
**Complexity:** Complex
**Model:** Opus

## Response

### Syscall Logger Kernel Module

```c
// syscall_logger.c
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/syscalls.h>
#include <linux/kallsyms.h>
#include <linux/kprobes.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Security Team");
MODULE_DESCRIPTION("Syscall logger using kprobes");
MODULE_VERSION("1.0");

// Kprobe for sys_execve
static int handler_pre_execve(struct kprobe *p, struct pt_regs *regs) {
    const char __user *filename;

#ifdef CONFIG_X86_64
    filename = (const char __user *)regs->di;  // First arg in RDI
#else
    filename = (const char __user *)regs->bx;  // ARM/other
#endif

    char buf[256];
    if (strncpy_from_user(buf, filename, sizeof(buf)) > 0) {
        pr_info("EXECVE: %s (PID: %d, UID: %d)\n",
                buf, current->pid, current_uid().val);
    }

    return 0;  // Continue execution
}

static struct kprobe kp_execve = {
    .symbol_name = "__x64_sys_execve",
    .pre_handler = handler_pre_execve,
};

// Kprobe for sys_open
static int handler_pre_open(struct kprobe *p, struct pt_regs *regs) {
    const char __user *filename;

#ifdef CONFIG_X86_64
    filename = (const char __user *)regs->di;
#else
    filename = (const char __user *)regs->bx;
#endif

    char buf[256];
    if (strncpy_from_user(buf, filename, sizeof(buf)) > 0) {
        // Only log sensitive paths
        if (strstr(buf, "/etc/passwd") || strstr(buf, "/etc/shadow")) {
            pr_warn("OPEN (sensitive): %s (PID: %d, UID: %d)\n",
                    buf, current->pid, current_uid().val);
        }
    }

    return 0;
}

static struct kprobe kp_open = {
    .symbol_name = "__x64_sys_openat",
    .pre_handler = handler_pre_open,
};

// Module initialization
static int __init syscall_logger_init(void) {
    int ret;

    pr_info("Syscall logger module loading...\n");

    // Register kprobe for execve
    ret = register_kprobe(&kp_execve);
    if (ret < 0) {
        pr_err("Failed to register kprobe for execve: %d\n", ret);
        return ret;
    }

    // Register kprobe for open
    ret = register_kprobe(&kp_open);
    if (ret < 0) {
        pr_err("Failed to register kprobe for open: %d\n", ret);
        unregister_kprobe(&kp_execve);
        return ret;
    }

    pr_info("Syscall logger active\n");
    return 0;
}

// Module cleanup
static void __exit syscall_logger_exit(void) {
    unregister_kprobe(&kp_execve);
    unregister_kprobe(&kp_open);
    pr_info("Syscall logger unloaded\n");
}

module_init(syscall_logger_init);
module_exit(syscall_logger_exit);
```

### Makefile

```makefile
obj-m += syscall_logger.o

KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean

install:
	sudo insmod syscall_logger.ko

uninstall:
	sudo rmmod syscall_logger

logs:
	sudo dmesg | tail -50
```

### Build & Load

```bash
# Compile module
make

# Load module
sudo insmod syscall_logger.ko

# Check module loaded
lsmod | grep syscall_logger

# View logs
sudo dmesg -w

# Trigger events
cat /etc/passwd     # Should log
ls /tmp            # Should NOT log (not sensitive)

# Unload module
sudo rmmod syscall_logger
```

### Output Example

```
[12345.678] syscall_logger: Syscall logger module loading...
[12345.679] syscall_logger: Syscall logger active
[12350.123] syscall_logger: EXECVE: /usr/bin/cat (PID: 1234, UID: 1000)
[12350.124] syscall_logger: OPEN (sensitive): /etc/passwd (PID: 1234, UID: 1000)
[12360.456] syscall_logger: Syscall logger unloaded
```

---

## Key Takeaways

1. **kprobes** — dynamic tracing without modifying kernel source
2. **pt_regs** — access syscall arguments from registers
3. **strncpy_from_user** — safe copy from userspace
4. **dmesg** — kernel log buffer (ring buffer, limited size)
5. **NEVER block** in kprobe handler (no sleep, no heavy processing)

**Security use case:** Detect credential theft, monitor sensitive file access
**Performance:** ~1-2µs overhead per syscall
**Alternative:** eBPF (safer, no kernel module required)
