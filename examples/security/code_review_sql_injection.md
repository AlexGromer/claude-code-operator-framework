# Example: Code Review

**Task Type:** Code review with security focus
**Complexity:** Medium
**Model:** Sonnet (balanced quality/cost)

---

## User Request

> Review this authentication function for security issues:
>
> ```python
> def authenticate_user(username, password):
>     db = connect_database()
>     query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
>     result = db.execute(query)
>     return len(result) > 0
> ```

---

## Claude's Reasoning Process

### 1. Initial Analysis
- **Language:** Python
- **Domain:** Authentication
- **Critical Areas:** SQL query construction, password handling
- **Risk Level:** HIGH (authentication logic)

### 2. Security Checklist
- [ ] SQL injection protection
- [ ] Password hashing
- [ ] Input validation
- [ ] Error handling
- [ ] Timing attack prevention

### 3. Identified Issues

#### 🔴 CRITICAL: SQL Injection (OWASP Top 10 #1)
- **Location:** Line 3 — string interpolation in SQL query
- **Risk:** Attacker can execute arbitrary SQL
- **Exploit Example:** `username = "admin' OR '1'='1' --"`
- **Impact:** Full database compromise, authentication bypass

#### 🔴 CRITICAL: Plaintext Password Storage
- **Location:** Line 3 — direct password comparison
- **Risk:** Passwords stored/compared in plaintext
- **Impact:** Mass account compromise if database breached

#### 🟡 MEDIUM: No Input Validation
- **Location:** Parameters not validated
- **Risk:** Unexpected input formats

#### 🟡 MEDIUM: Boolean Timing Attack
- **Location:** `len(result) > 0` reveals user existence
- **Risk:** Username enumeration

---

## Claude's Response

### Security Issues Found

I've identified **2 critical** and **2 medium** security vulnerabilities in this authentication function:

#### 1. 🔴 SQL Injection (CRITICAL)
**Problem:** The SQL query uses string interpolation (`f-string`), making it vulnerable to SQL injection attacks.

**Exploit Example:**
```python
# Attacker input
username = "admin' OR '1'='1' --"
password = "anything"

# Resulting query
"SELECT * FROM users WHERE username='admin' OR '1'='1' --' AND password='anything'"
# This bypasses authentication!
```

**Fix:** Use parameterized queries:
```python
query = "SELECT * FROM users WHERE username=? AND password=?"
result = db.execute(query, (username, password))
```

#### 2. 🔴 Plaintext Password Storage (CRITICAL)
**Problem:** Passwords are compared directly, implying plaintext storage.

**Fix:** Use password hashing (bcrypt/argon2):
```python
import bcrypt

# At registration
hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# At login
query = "SELECT password_hash FROM users WHERE username=?"
result = db.execute(query, (username,))
if result:
    stored_hash = result[0]['password_hash']
    return bcrypt.checkpw(password.encode(), stored_hash)
```

#### 3. 🟡 Username Enumeration (MEDIUM)
**Problem:** Function reveals whether username exists via timing/return value.

**Fix:** Use constant-time comparison and generic error messages.

#### 4. 🟡 Missing Input Validation (MEDIUM)
**Problem:** No validation of input length or format.

**Fix:** Add validation:
```python
if not username or len(username) > 255:
    raise ValueError("Invalid username")
```

---

### Secure Implementation

Here's a complete rewrite following security best practices:

```python
import bcrypt
from typing import Optional

def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user with secure practices.

    Args:
        username: User's username
        password: User's plaintext password (will be compared to hash)

    Returns:
        True if authenticated, False otherwise

    Security measures:
    - Parameterized queries (SQL injection prevention)
    - Password hashing (bcrypt with salt)
    - Input validation
    - Constant-time comparison (timing attack prevention)
    - Comprehensive error handling
    """
    # Input validation
    if not username or not isinstance(username, str):
        return False
    if not password or not isinstance(password, str):
        return False
    if len(username) > 255 or len(password) > 128:
        return False

    try:
        db = connect_database()

        # Parameterized query (SQL injection prevention)
        query = "SELECT password_hash FROM users WHERE username = ?"
        result = db.execute(query, (username,))

        if not result:
            # User not found — use fake hash to prevent timing attacks
            fake_hash = bcrypt.hashpw(b"fake", bcrypt.gensalt())
            bcrypt.checkpw(password.encode(), fake_hash)
            return False

        stored_hash = result[0]['password_hash']

        # Secure password verification (constant-time comparison)
        is_valid = bcrypt.checkpw(password.encode(), stored_hash)

        return is_valid

    except Exception as e:
        # Log error (don't expose to user)
        log_security_error("Authentication failed", username, e)
        return False

    finally:
        db.close()
```

---

### Testing Recommendations

1. **Unit Tests:**
   ```python
   def test_sql_injection_prevention():
       result = authenticate_user("admin' OR '1'='1' --", "any")
       assert result == False

   def test_valid_credentials():
       # Assume user exists with bcrypt hash
       result = authenticate_user("alice", "correct_password")
       assert result == True
   ```

2. **Security Tests:**
   - SQL injection (automated: `sqlmap`)
   - Timing attacks (measure response time variance)
   - Password strength requirements

3. **Integration Tests:**
   - Failed login handling
   - Rate limiting (prevent brute force)
   - Account lockout after N failed attempts

---

### References

- **OWASP Top 10:** A03:2021 — Injection
- **CWE-89:** SQL Injection
- **CWE-256:** Plaintext Storage of Passwords
- **NIST SP 800-63B:** Digital Identity Guidelines

---

## Key Takeaways (for Claude)

**This example demonstrates:**

1. **Structured Analysis**
   - Security checklist approach
   - Risk-based prioritization (critical → medium → low)
   - Specific locations and examples

2. **Actionable Recommendations**
   - Not just "use parameterized queries" → **show exact code**
   - Include error handling, edge cases
   - Provide testing strategy

3. **Educational Value**
   - Explain WHY it's vulnerable (exploit example)
   - Reference standards (OWASP, CWE, NIST)
   - Balance thoroughness with readability

4. **Professional Tone**
   - No alarmism ("this will get you hacked")
   - Focus on fixes, not blame
   - Provide complete, production-ready code

**Complexity Routing:** Medium → **Sonnet** (security analysis, code generation)
